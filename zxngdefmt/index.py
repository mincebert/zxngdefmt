# zxngdefmt/index.py



import re

from .token import (
    LINK_RESTR,
    renderstring,
)



# width for the term list in an index
TERM_WIDTH = 20

# minimum number of spaces to leave between a term and the start of the
# references for an index entry
TERM_GAP = 3


# TODO

INDEX_RE = re.compile(r'\s{,2}'

                      + '('
                      + LINK_RESTR
                      + r"|(?P<static_text>\S+(\s{,2}\S+)*)"
                      + r")?"

                      + r"(\s{3,}(?P<remainder>.+))?")

INDEX_REF_RE = re.compile(LINK_RESTR + r"(,\s+(?P<remainder>.+))?")



def linkcmd(text, target):
    return '@{"' + text + '" LINK ' + target + '}'


def _itermore(iterable):
    """Pass through all values from the given iterable, augmented by the
    information if there are more values to come after the current one
    (True), or if it is the last value (False).
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



class GuideIndex(dict):
    """TODO
    """


    def __init__(self):
        super().__init__()

        self._warnings = []


    def __repr__(self):
        return "GuideIndex(" + super().__repr__() + ')'


    def parseline(self, line, prev_term=None):
        m = INDEX_RE.match(line)
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


    def format(self, line_maxlen, term_width=TERM_WIDTH, term_gap=TERM_GAP):
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

            if len(term_text) + term_gap > term_width:
                index_lines.append(line_markup)
                tab = ' ' * term_width
                line_render += tab
                line_markup += tab
            else:
                tab = ' ' * (term_width - len(term_text))
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
                    line_markup = line_render = ' ' * term_width

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
