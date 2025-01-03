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
            if node_name in self._nodes:
                doc.addwarning(
                    f"node: @{node_name} same name already exists in"
                    f" document: {self._nodes[node_name]} -"
                    f" ignoring")

                continue

            # record this node as in this document
            self._nodes[node_name] = doc_name


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
        """

        # try to parse index entry from this line - this should always
        # succeed but just return empty matching groups for some key
        # things but, if it doesn't, we return None for 'no match'
        m = INDEX_LINE_RE.match(line)
        if not m:
            self._warnings.append(
                "cannot parse index entry from line: " + line)

            return None

        term_text, term_target, term_static, refs = (
            m.group("link_text", "link_target", "static_text", "refs"))

        # get the term for this entry in order or preference
        term_markup = term_text or term_static or prev_term

        # if we haven't got a term from this line, nor is there one
        # continued from the previous line, skip this line
        if not term_markup:
            self._warnings.append(
                "no term or previous term on index line: " + line)

            return None

        # get the text for the term from the link command
        term = renderstring(term_markup.strip())

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
        if (not term_target) and (not refs_dict):
            return None

        term_dict = {}

        if term_target:
            term_dict["target"] = term_target
        term_dict["refs"] = refs_dict

        self._addterm(term, term_dict)

        # we added something to the index, so return the term we used,
        # so it can be used for prev_term on the next line, if required
        return term


    def merge(self, merge_index):
        """TODO
        """

        for term in merge_index:
            self._addterm(term, merge_index[term])

        self._warnings.extend(merge_index._warnings)


    def format(self, line_maxlen, refs_indent=DEFAULT_REFS_INDENT, refs_gap=DEFAULT_REFS_GAP):
        prev_term_text = None
        prev_term_alphanum = None

        index_lines = []

        for term_text in sorted(self,
                                key=lambda s: s.lower()
                                                  if re.match("[0-9A-Z]", s)
                                                  else (' ' + s)):

            term_alphanum = bool(re.match(r"[0-9A-Z]", term_text))
            if prev_term_text:
                if term_alphanum != prev_term_alphanum:
                        index_lines.append('')

                elif term_alphanum and (term_text[0] != prev_term_text[0]):
                    index_lines.append('')

            term = self[term_text]

            line_render = term_text
            line_markup = (linkcmd(term_text, term["target"])
                                if term.get("target") else term_text)

            if len(term_text) + refs_gap > refs_indent:
                index_lines.append(line_markup)
                tab = ' ' * refs_indent
                line_render += tab
                line_markup += tab
            else:
                tab = ' ' * (refs_indent - len(term_text))
                line_render += tab
                line_markup += tab

            refs = term["refs"]

            line_first = True
            for ref, more in _itermore(sorted(refs)):
                ref_text = ' ' + ref + ' '

                ref_pre = '' if line_first else ' '
                ref_post = ',' if more else ''

                if len(line_render + ref_pre + ref_text + ref_post) > line_maxlen:
                    index_lines.append(line_markup)

                    # start new indented line
                    line_markup = line_render = ' ' * refs_indent

                    ref_pre = ''

                    line_first = True
                else:
                    line_first = False

                line_markup += ref_pre + linkcmd(ref_text, refs[ref]) + ref_post
                line_render += ref_pre + ref_text + ref_post

            index_lines.append(line_markup)

            prev_term_text = term_text
            prev_term_alphanum = term_alphanum

        return index_lines
