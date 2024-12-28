# zxngdefmt/node.py



import re

from .index import GuideIndex
from .token import (
    LINK_RE,
    LITERALLINE_RE,
    TOKEN_RE,
    rendertoken,
)


# maximum length for a single line in the output guide
#
# TODO: also in doc

LINE_MAXLEN = 80



class GuideNodeDocs(dict):
    def fixlink(self, doc_name, target):
        """This function is passed as the parameter for 'repl' to
        the re.sub() function, to add the 'Document/' prefix to a
        link target, if it is in another document in the set.

        Warnings will also be generated if a link target is does not
        exist.
        """

        # if the link is local (not to another document) ...
        if '/' not in target:
            # ... and the target is a node in the set
            if target not in self:
                return

            if self[target] != doc_name:
                return self[target] + '/' + target

        # return the (possibly rewritten) link target
        return target



class GuideNode(object):
    """Represents a node (page in a NextGuide document).

    TODO
    """


    def __init__(self, name):
        """Initialise a new node with the specified name.
        """

        super().__init__()

        # initialise the current node with the specified name
        self.name = name

        # no links to other documents yet
        self._links = {}

        # no lines yet
        self._lines = []

        # initialise list of warnings encountered
        self._warnings = []


    def __repr__(self):
        return f"GuideNode(@{self.name})"


    def setlink(self, link, node):
        """Unconditionally set the link to another node.  This is used
        when a node explicitly sets the link.
        """

        self._links[link] = node


    def setdefaultlink(self, link, node):
        """Set the link to another node only if this link is not yet
        defined.  This used when the entire document is completed and
        the missing links are filled in.
        """

        if node:
            self._links.setdefault(link, node)


    def getlink(self, link):
        """Return the link to the specified target from this node, or
        None if it is not defined.
        """

        return self._links.get(link)


    def addwarning(self, warning):
        """Add a warning to the list of warnings about this node.
        """

        self._warnings.append(warning)


    def getwarnings(self):
        """Return a list of warnings about this node.
        """

        return self._warnings


    def appendline(self, l):
        """Add a raw line to the current node.
        """

        self._lines.append(l)


    def parseindex(self):
        """Parse index entries.

        TODO
        """

        index = GuideIndex()
        prev_term = None

        for line in self._lines:
            term = index.parseline(line, prev_term)
            prev_term = term

        return index


    def write(self, *, doc_name=None, node_docs={}):
        # the current line being assembled
        line_markup = ""
        line_render = ""

        # any spaces
        pre_space = ""

        word_markup = ""
        word_render = ""


        # formatted lines in the output
        output = ["@node " + self.name]

        for link in ["prev", "next", "toc", "index"]:
            if link in self._links:
                output.append(f"@{link} {self._links[link]}")


        def writeline():
            nonlocal output, line_markup, line_render, pre_space

            if line_markup:
                output.append(line_markup)

                line_markup = ""
                line_render = ""

                pre_space = ""


        def completeword(space=""):
            """TODO
            """

            nonlocal line_markup, line_render, pre_space, word_markup, word_render

            # if no line or word, we have nothing to complete nor return, so
            # we're done
            if (not line_render) and (not word_render):
                return

            # start with no completed line to return and check if the stored
            # space and rendered word would fit on this line
            if (len(line_render + pre_space + word_render) > LINE_MAXLEN):
                # adding the current word would make it over length - render it
                writeline()

                # don't add the space, as we're beginning a new line

            else:
                # the current word will fit on this line - add the space, as
                # we're continuing the line
                line_markup += pre_space
                line_render += pre_space

            # add the current word to the line (either freshly cleared, or
            # continuing the current one)
            line_markup += word_markup
            line_render += word_render

            # start a new word with the supplied previous space
            pre_space = space
            word_markup = ""
            word_render = ""


        def appendtoken(t):
            """TODO
            """

            nonlocal word_markup, word_render

            word_markup += t
            word_render += rendertoken(t)


        def fixlink_repl(m):
            link_text, link_target = m.group("link_text", "link_target")
            fixed_target = node_docs.fixlink(doc_name, link_target)
            if fixed_target is None:
                self._warnings.append(
                    f"link target: @{link_target} does not exist")
            return '@{"' + link_text + '" LINK ' + (fixed_target or link_target) + '}'


        for line in self._lines:
            # if a link is to a node in another document in the set,
            # prefix the link with 'Document/'
            #
            # this will also report on links targets which don't exist
            line = re.sub(LINK_RE, fixlink_repl, line)

            # if the line is blank or is one that is used literally,
            # just add that to the document
            if (line == '') or re.match(LITERALLINE_RE, line):
                # finish the current line and append it
                writeline()

                # add the literal line
                output.append(line)

                continue

            # go through the line matching tokens (markup, literal or spaces)
            remainder = line
            while remainder:
                m = re.match(TOKEN_RE, remainder)

                if not m:
                    raise AssertionError(
                        "failed to match next token in: " + remainder)

                token, remainder = m.group("token", "remainder")
                #print(f"TOKEN >>> <{token}>")
                #print(f"REMAINDER >>> <{remainder}>")

                if m.group("space"):
                    # token is a space, complete the current word
                    completeword(space=token)

                else:
                    # token is not a space - add it
                    appendtoken(token)

            # end of line completes a word and adds a space
            completeword(space=" ")

        # if there is something in the buffer
        writeline()

        return output
