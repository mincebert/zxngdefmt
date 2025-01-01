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
    # as a 'remainder', which we parse separately
    + r"(\s{3,}(?P<remainder>.+))?")


# this regular expression matches references (the right column) one at a
# time from the 'remainder' column in the line expression, above

INDEX_REF_RE = re.compile(
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

    # Get an iterator and pull the first value.
    i = iter(iterable)
    try:
        prev = next(i)
    except StopIteration:
        return
    # Run the iterator to exhaustion (starting from the second value).
    for v in i:
        # Report the *previous* value (more to come).
        yield prev, True
        prev = v
    # Report the last value.
    yield prev, False



class GuideNodeDocs(dict):
    """Represents a mapping between a node name (held in the key of a
    dict) and the document it's in.  This is used to fix links to nodes
    nodes in other documents by prefixing them with the document name.
    """


    def addnodes(self, doc):
        """Merge in a list of node names from a document.
        """

        # go through the nodes in this new document
        for node_name in doc.getnodenames():
            # if a node with this name already exists, record a
            # warning in the document and skip adding it
            if node_name in self:
                doc.addwarning(
                    f"node: @{node_name} same name already exists in"
                    f" document: {self[node_name]} -"
                    f" ignoring")

                continue

            # record this node as in this document
            self[node_name] = doc.getname()


    def exists(self, target):
        if '/' in node:
            return True

        return node in self


    def fixlink(self, doc_name, target):
        """This function is passed as the parameter for re.sub(repl=) to
        add the 'Document/' prefix to a link target node name
        ('target'), if it is in a different document (from 'doc_name',
        the one supplied).

        If the target node name could not be found, None is returned;
        the caller can use this to correct the link or flag up an error.
        """

        # if the link is already qualified with a document name, assume
        # it's correct and leave it alone
        if '/' in target:
            return target

        # if the target node was not found, return None
        if target not in self:
            return

        # if the target node is in this document, return it unqualified
        if self[target] == doc_name:
            return target

        # the target is in another document - qualify it
        return self[target] + '/' + target



class GuideIndex(dict):
    """TODO
    """


    def __init__(self):
        super().__init__()

        self._warnings = []


    def __repr__(self):
        return "GuideIndex(" + super().__repr__() + ')'


    def parseline(self, line, prev_term=None):
        m = INDEX_LINE_RE.match(line)
        if not m:
            raise ValueError("cannot parse link from line: " + line)

        link_text, link_target, static_text, refs = (
            m.group("link_text", "link_target", "static_text", "remainder"))

        # if we haven't got a term from this line, nor is there one
        # continuing from the previous line, skip this one
        term_markup = link_text or static_text or prev_term
        if not term_markup:
            self._warnings.append("no term or previous term on index"
                                  " line: " + line)

            return None

        term = renderstring(term_markup.strip())

        refs_dict = {}
        while refs:
            m = INDEX_REF_RE.match(refs)
            if not m:
                break
            ref_text, ref_target, refs = (
                m.group("link_text", "link_target", "remainder"))
            refs_dict[ref_text.strip()] = ref_target

        # if no link targe in the term, nor any refs, this probably is
        # not an index entry but some plain text - ignore this line and
        # return that we're not in a term
        if (not link_target) and (not refs_dict):
            return None

        self.setdefault(term, {})
        self[term].setdefault("target", link_target)
        self[term].setdefault("refs", {})
        self[term]["refs"].update(refs_dict)

        return term


    def merge(self, merge_index):
        """TODO
        """

        for term in merge_index:
            self.setdefault(term, {})
            self_term = self[term]

            merge_term = merge_index[term]
            if merge_term["target"]:
                self_term["target"] = merge_term["target"]

            self_term.setdefault("refs", {})
            self_term["refs"].update(merge_term["refs"])


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
