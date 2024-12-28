# zxngdefmt/index.py



import re

from .token import (
    LINK_RE,
    renderstring,
)



# TODO

INDEX_RE = (r'('
            + LINK_RE
            + r"|(?P<static_text>\S+(\s{,2}\S+)*)"
            + r")?"
            + r"(\s{3,}(?P<remainder>.+))?")

INDEX_REF_RE = LINK_RE + r"(,\s+(?P<remainder>.+))?"



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


    def __repr__(self):
        return "GuideIndex(" + super().__repr__() + ')'


    def parseline(self, line, prev_term=None):
        line = line.strip()

        m = re.match(INDEX_RE, line)
        if not m:
            raise ValueError("cannot parse link from line: " + line)

        link_text, link_target, static_text, refs = (
            m.group("link_text", "link_target", "static_text", "remainder"))

        term = renderstring((link_text or static_text or prev_term).strip())

        refs_dict = {}
        while refs:
            m = re.match(INDEX_REF_RE, refs)
            if not m:
                break
            ref_text, ref_target, refs = (
                m.group("link_text", "link_target", "remainder"))
            refs_dict[ref_text.strip()] = ref_target

        if (not link_target) and (not refs_dict):
            return term

        self.setdefault(term, {})
        self[term].setdefault("target", link_target)
        self[term].setdefault("refs", {})
        self[term]["refs"].update(refs_dict)

        return term


    def format(self, term_width=20, doc_width=80):
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

            if "target" in term:
                line = linkcmd(term_text, term["target"])
            else:
                line = term_text

            if len(term_text) + 3 > term_width:
                index_lines.append(line)
                line = ' ' * term_width
            else:
                line += ' ' * (term_width - len(term_text))

            refs = term["refs"]

            line_first = True
            for ref, more in _itermore(sorted(refs)):
                ref_text = ' ' + ref + ' '

                ref_pre = '' if line_first else ' '
                ref_post = ',' if more else ''

                if len(line + ref_pre + ref_text + ref_post) > doc_width:
                    index_lines.append(line)

                    # start new indented line
                    line = ' ' * term_width

                    ref_pre = ''

                    line_first = True
                else:
                    line_first = False

                line += ref_pre + linkcmd(ref_text, refs[ref]) + ref_post

            index_lines.append(line)

            prev_term_text = term_text
            prev_term_alphanum = term_alphanum

        return '\n'.join(index_lines)
