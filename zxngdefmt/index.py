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

        self[term] = { "target": link_target, "refs": refs_dict }

        return term
