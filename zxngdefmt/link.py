# zxngdefmt/link.py

# Clases for managing links between documents and indices.



import re

from .token import LINK_RESTR, renderstring



# --- constants ---



# default indent for the references (right) columnn in a formatted
# (generated) index - this is the width of the terms (left) column

DEFAULT_REFS_INDENT = 20


# minimum number of spaces to leave between a term and the start of the
# references for an index entry in a formatted index - if term width +
# refs gap is > refs indent (above), the references will start on the
# following line

DEFAULT_REFS_GAP = 3


# regular expressions for matching a line in a defined index page in a
# source file

# the first one matches the 'term' (the left column) and leaves the
# references as a remainder to be parsed by the second expression, below

INDEX_LINE_RE = re.compile(
    # lines can begin with 0-2 spaces
    r'\s{,2}'

    # a line can have a 'term' (in the left hand column) which is a
    # block of static text or a link
    #
    # if this is omitted, the term will be continued from the previous
    # line (this is handled elsewhere)
    + '('
    + LINK_RESTR
    + r"|(?P<static_text>\S+(\s{,2}\S+)*)"
    + r")?"

    # optionally followed by 3 or more spaces and a list of references
    # as 'refs', which we parse separately, using the expression below
    + r"(\s{3,}(?P<refs>.+))?")


# this regular expression matches references (the right column) one at a
# time from the 'remainder' column in the line expression, above

INDEX_REFS_RE = re.compile(
    # the references column contains a link
    LINK_RESTR

    # the remainder (if present) is separately by a comma and optional
    # space
    + r"(,\s*(?P<remainder>.+))?")



# --- functions ---



def linkcmd(text, target):
    """Generate a command for a link, given the specified text and a
    target.
    """

    return '@{"' + text + '" LINK ' + target + '}'


def _itermore(iterable):
    """Returns a generator yielding a tuple consisting of two values.
    The first is the next iteration of the supplied iterable, and the
    second is a boolean that indicates if there are more items available
    in the iterable.  The second value will be True for all iterations
    except the last.
    """

    # get an iterator for the iterable
    i = iter(iterable)

    try:
        # try to get the first item
        item = next(i)

    except StopIteration:
        # it failed, we're done (with no items)
        return

    # iterate through the items in the iterable, starting with the
    # second (as we got the first, above)
    for next_ in i:
        # return the item retrieved last time and True, to signal there
        # are more items to come
        yield item, True

        # store the item we retreived this time to return next time
        item = next_

    # we've exhausted the iterable - return the item we got last time
    # and False, to indicate there are no more items available
    yield item, False

    # no further items, so the generator will stop here



# --- classes ---



class GuideNodeDocs(object):
    """Represents a mapping between a node name (held in the key of a
    dict) and the document it's in.  This is used to fix links to nodes
    in other documents by prefixing them with the document name.
    """


    def __init__(self):
        """Initialise a GuideNodeDocs object.
        """

        super().__init__()

        # initialise the dictionary of nodes to be empty
        self._nodes = {}

        # initialise the set of 'always local' nodes which exist in all
        # documents across a set and links are never rewritten to a node
        # in another document
        self._local_nodes = set()


    def __repr__(self):
        """Printable version of the object useful for debugging.
        """

        return "GuideNodeDocs(" + repr(sorted(self._nodes)) + ')'


    def __contains__(self, name):
        """Reports if a particular node name is present in the mapping
        dictionary.
        """

        return name in self._nodes


    def addnodes(self, doc):
        """Merge the names of all the nodes in a GuideDoc document (and
        the name of that document) to the mapping dictionary.
        """

        # get the name of the document
        doc_name = doc.getname()

        # go through the nodes in this new document
        for node_name in doc.getnodenames():
            # if a node with this name already exists, add a warning to
            # the document and skip adding it
            if ((node_name not in self._local_nodes)
                and (node_name in self._nodes)):

                doc.addwarning(
                    f"node: @{node_name} same name already exists in"
                    f" document: {self._nodes[node_name]} -"
                    f" ignoring")

                continue

            # record this node as in this document
            self._nodes[node_name] = doc_name


    def addlocalnode(self, node_name):
        """Add the named local node to the set of nodes which can
        exist across all documents in a set.
        """

        self._local_nodes.add(node_name)


    def fixlink(self, doc_name, target_name):
        """This function is supplied the name of a target node for a
        link and the name of the document in which that link occurs.
        The mapping dictionary is checked and, if the target is in a
        different document, the link will be prefixed with 'Document/'.

        If the target is in the same document, it is NOT qualified with
        the document name and returned as is.

        If the target is already prefixed with a document name, it is
        assumed that the author explicitly wanted that document and it
        is also left alone, regardless of whether that document is one
        referred to in the mapping dictionary.

        If the target node name could not be found, None is returned;
        the caller can use this to correct the link or flag up an error.
        """

        # if the link is already qualified with a document name, assume
        # it's correct and leave it alone
        if '/' in target_name:
            return target_name

        # if the target node was not found, return None
        if target_name not in self._nodes:
            return

        # if the target node is in the 'always local' set, just return
        # unqualified
        if target_name in self._local_nodes:
            return target_name

        # if the target node is in this document, return it unqualified
        if self._nodes[target_name] == doc_name:
            return target_name

        # the target is in another document - qualify it
        return self._nodes[target_name] + '/' + target_name



class GuideIndex(object):
    """Represents the index node of a document.  The class provides
    methods to parse indexes in a specific source format and then render
    them out again.

    In addition, indices across multiple documents can be merged to
    provide a common index across the set.

    For the purposes of this class, indexes have a simple, consistent
    structure.  Each entry is structured as follows:

    - each entry is called a 'term' and has a name, which is displayed
    in the index

    - each term may optionally have a link to a node giving the primary
    definition

    - each term may optionally have one or more secondary 'references',
    which each have display text and a link to a node (which is
    non-optional)
    """


    def __init__(self):
        """Initialise a GuideIndex object.
        """

        super().__init__()

        # initialise the dictionary of terms to be empty
        self._terms = {}

        # initialise the list of warnings to be empty
        self._warnings = []


    def __repr__(self):
        """Printable version of the object useful for debugging.
        """

        return "GuideIndex(" + repr(sorted(self._terms)) + ')'


    def __contains__(self, term_text):
        """Returns if the specified term text is present in the index.
        """

        return term_text in self._terms


    def __getitem__(self, term_text):
        """Get a dictionary entry giving details for the specified term.

        The returned value should be considered opaque and this method
        is really only intended for internal use.  However, the return
        value is a dictionary consisting of the following keys:

        target -- a string giving the link target for the primary
        definition (or None, if there is none)

        refs -- a dictionary giving the secondary references for the
        term; the dictionary keys are the reference text and the values
        against those keys the reference target node
        """

        return self._terms[term_text]


    def __iter__(self):
        """Return an iterator for walking through the terms in the
        index.
        """

        return iter(self._terms)


    def getwarnings(self):
        """Return the warnings from the index.
        """

        return self._warnings


    def _addterm(self, add_term_text, add_term_dict):
        self_term = self._terms.setdefault(add_term_text, {})

        # if this entry specifies a primary target for the term, set it
        if add_term_dict.get("target"):
            if "target" in self_term:
                if add_term_dict["target"] != self_term["target"]:
                    # there is already a primary target for this term
                    # and it's different - add a warning but don't
                    # change it
                    self._warnings.append(
                        f"term: '{add_term_text}' with target:"
                        f" {add_term_dict['target']} already exists"
                        " with different target:"
                        f" {self_term['target']}")

            # ... or, if the target is not yet set, set it to this entry
            else:
                self_term["target"] = add_term_dict["target"]

        # go through the references and add them to the term entry
        self_refs = self_term.setdefault("refs", {})
        for add_ref in add_term_dict["refs"]:
            add_ref_target = add_term_dict["refs"][add_ref]
            if add_ref in self_refs:
                if add_ref_target != self_refs[add_ref]:
                    # a reference with the same text was found but the
                    # target was different - add a warning but don't
                    # change it
                    self._warnings.append(
                        f"term: '{add_term_text}' has reference:"
                        f" '{add_ref}' with target: {add_ref_target}"
                        " already exists with different target:"
                        f" {self_refs[add_ref]}")
            else:
                self_refs[add_ref] = add_ref_target


    def parseline(self, line, prev_term=None):
        """Parse a line from a source index node and add the results to
        the index held by this object.

        Lines should be of the form:

        - begin with 0-2 spaces

        - have a term which is a block of static text or a link command;
        if this is omitted, the line will continue the previous term
        specified with prev_term

        - optionally followed by 3 or more spaces and a list of
        references, which must all be link commands

        The text part of term matched is returned, if an entry was
        parsed - this is returned; it can be supplied as the prev_term
        parameter for the next line and will be used if the following
        line doesn't have a term (allowing a term's references to be
        spread over multiple lines).  If a line is matched and continues
        the prev_term, this term will be returned for this call.

        If there are any problems adding an entry, such as duplicate
        entries for the same term or reference with conflicting target
        link information, warnings will be added.
        """

        # try to parse index entry from this line - this should always
        # succeed but just return empty matching groups for some key
        # things but, if it doesn't, we return None for 'no match'
        m = INDEX_LINE_RE.match(line)
        if not m:
            self._warnings.append(
                "cannot parse index entry from line: " + line)

            return None

        term_link_text, term_link_target, term_static, refs = (
            m.group("link_text", "link_target", "static_text", "refs"))

        # get the term for this entry in order or preference
        term_text_markup = term_link_text or term_static or prev_term
        if not term_text_markup:
            # no valid term was found - ignore this line
            return None

        # render the text to remove formatting from the term dictionary
        term_text = renderstring(term_text_markup.strip())

        # loop whilst there are more references to parse, collecting
        # them into refs_dict
        refs_dict = {}
        while refs:
            # try to match the first reference entry
            m = INDEX_REFS_RE.match(refs)

            # no match - we're done with this line
            if not m:
                break

            # get the parts of the reference entry
            ref_text, ref_target, refs = (
                m.group("link_text", "link_target", "remainder"))

            # store it in the dict
            refs_dict[ref_text.strip()] = ref_target

        # if no link target in the term, nor any refs, this probably is
        # not an index entry but some plain text - ignore this line and
        # return that we're not in a term
        if (not term_link_target) and (not refs_dict):
            return None

        # build a dictionary of details about the term (except the text)
        # to use with _addterm()
        term_dict = {}
        if term_link_target:
            term_dict["target"] = term_link_target
        term_dict["refs"] = refs_dict

        # add the term to the dictionary, flagging up any warnings about
        # duplicates, etc.
        self._addterm(term_text, term_dict)

        # we added something to the index, so return the term we used,
        # so it can be used for prev_term on the next line, if required
        return term_text


    def merge(self, merge_index):
        """Merge another index into this one to create a common index
        (e.g. across a set).

        If there are any problems adding an entry, such as duplicate
        entries for the same term or reference with conflicting target
        link information, warnings will be added.
        """

        # go through the terms in the index we're merging and merge them
        # into this one
        for term in merge_index:
            self._addterm(term, merge_index[term])


    def format(self, line_maxlen, terms_width=DEFAULT_REFS_INDENT,
               terms_gap=DEFAULT_REFS_GAP):
        """Format the index for writing.  The terms will be listed on
        the left side, with the references on the right side, wrapped
        to the maximum line width.  The return value is a list of lines.

        The width of the terms column will be terms_width, the
        references starting after that.  A minimum of terms_gap spaces
        will be left between a term and a reference - if a term is
        longer than this, the references will start on the following
        line.

        The terms are sorted into ASCIIbetical order, with all the non
        numeric and alphabetic characters coming first.  Blank lines
        will be inserted between the symbols and alphanumeric
        characters, as well as between each number and letter group.
        """

        # store the previous term group (space for a symbol [see below],
        # number or letter) - this is used to work out when to insert a
        # blank line
        prev_term_group = None

        # counter for the number of links (used to track if the limit of
        # 255 is exceeded)
        num_links = 0

        # initialise the returned lines list with 'Index' centred and a
        # following blank line before the terms start
        index_lines = ["@{c}@{h1}Index", ""]

        # work through the terms, sorted symbols first, then numbers,
        # then letters; the symbols are moved first (but retaining
        # ASCIIbetical order) by prefixing them with a space character)
        for term_text in (
            sorted(self,
                   key=lambda s: s.lower()
                                     if re.match("[0-9A-Z]", s, re.IGNORECASE)
                                     else (' ' + s))):

            # get the grouping of this term, based on the first
            # character, if it's 0-9 or A-Z (anything else returns an
            # empty string, so are grouped under that)
            term_group = re.match(
                r"([0-9A-Z]?)", term_text, re.IGNORECASE).group(1)

            # if the group of this term is different from the previous
            # one, we need to insert a blank line
            if ((prev_term_group is not None)
                and (term_group != prev_term_group)):
                    index_lines.append('')

            # get the dictionary about this term
            term_dict = self[term_text]

            # add the term to the rendered and markup versions of the
            # output
            #
            # the rendered version is used to calculate displayed widths
            # for word wrap; the markup version is used for the actual
            # output
            line_render = ' ' + term_text + ' '
            line_markup = (linkcmd(' ' + term_text + ' ', term_dict["target"])
                               if term_dict.get("target")
                               else (" @{b}" + term_text + "@{ub} "))

            # increase the number of links, if the term has a target set
            if term_dict.get("target"):
                num_links += 1

            # get the dictionary of references for this term
            refs_dict = term_dict["refs"]

            # if there are references, we need to space over to the
            # references column from the term
            if refs_dict:
                # if the length of the rendered version, added to the
                # minimum gap between it and the references, is over the
                # width of the terms column, write out the term on a
                # line of it's own and start a new line for the
                # references
                if len(line_render) + terms_gap > terms_width:
                    index_lines.append(line_markup)

                    tab = ' ' * terms_width
                    line_render += tab
                    line_markup += tab


                # the term and gap will fit in the terms column - add
                # the number of spaces required to get into the
                # references column
                else:
                    tab = ' ' * (terms_width - len(line_render))
                    line_render += tab
                    line_markup += tab

            # start with this being the first reference on a line
            line_first = True

            # work through the references, getting the reference name
            # and flag if there are more references to come
            for ref, more in _itermore(sorted(refs_dict)):
                # references are space-padded at start and end
                ref_text = ' ' + ref + ' '

                # if the term is not the first on a line, it needs a
                # space to separate it from the previous term
                ref_pre = '' if line_first else ' '

                # we need a comma after the reference if there are more
                # to come
                ref_post = ',' if more else ''

                # if adding this reference to the line would cause it to
                # be overlength, finish that line and start a new one
                if (len(line_render + ref_pre + ref_text + ref_post)
                        > line_maxlen):

                    # write out this line
                    index_lines.append(line_markup)

                    # start new, indented line
                    line_markup = line_render = ' ' * terms_width

                    # we don't need the space before this term as this
                    # will be the first on the line
                    ref_pre = ''

                # add this reference to the render and markup versions
                # of the line
                line_render += ref_pre + ref_text + ref_post
                line_markup += (
                    ref_pre + linkcmd(ref_text, refs_dict[ref]) + ref_post)

                # we're no longer the first term on the line (even if
                # started a new one, we just added one that was the
                # first)
                line_first = False

                num_links += 1

            # add the last (uncompleted) line for this term the output
            index_lines.append(line_markup)

            # this term group as the previous, ready for the next one
            prev_term_group = term_group

        # generate a warning, if there are too many links in the index
        # node
        if num_links > 255:
            self._warnings.append(
                f"index node contains too many links: {num_links}")

        # return the formatted index
        return index_lines
