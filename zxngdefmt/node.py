# zxngdefmt/node.py

# Nodes are pages in NextGuide.



import re

from .index import GuideIndex

from .token import (
    LINK_RE,
    LITERALLINE_RE,
    TOKEN_RE,
    rendertoken,
)



# --- constants ---



# _NODE_LINK_TYPES = set
#
# Valid types of links from a node.

_NODE_LINK_TYPES = ["prev", "next", "toc"]



# --- classes ---



class GuideNodeDocs(dict):
    """Represents a mapping between a node name (held in the key of a
    dict) and the document it's in.  This is used to fix links to nodes
    nodes in other documents by prefixing them with the document name.
    """

    def fixlink(self, doc_name, target):
        """This function is passed as the parameter for re.sub(repl=) to
        add the 'Document/' prefix to a link target node name
        ('target'), if it is in a different document (from 'doc_name',
        the one supplied).

        If the target node name could not be found, None is returned;
        the caller can use this to correct the link or flag up an error.
        """

        # check if the link is not already qualified with a document name ...
        if '/' not in target:
            # if the target node was not found, return None
            if target not in self:
                return

            # if the target node is in this document - return it unqualified
            if self[target] == doc_name:
                return target

        # the target is in another document - qualify it
        return self[target] + '/' + target



class GuideNode(object):
    """Represents a node (page in a NextGuide document).

    TODO
    """


    def __init__(self, name):
        """Initialise a new node.
        """

        super().__init__()

        # store the name
        self.name = name

        # initialise the list of lines in the node
        self._lines = []

        # initialise the links to other nodes (prev/next/contents)
        self._links = {}

        # initialise list of warnings encountered
        self._warnings = []


    def __repr__(self):
        return f"GuideNode(@{self.name})"


    def setlink(self, link, target):
        """Unconditionally set the link to another node (prev/next/contents).
        This is used when a node explicitly sets the link.
        """

        # check the link is of a valid type
        if link not in _NODE_LINK_TYPES:
            return ValueError(f"node: @{self.name} set invalid link type:"
                              f" {link}")

        self._links[link] = target


    def setdefaultlink(self, link, target):
        """Set the link to another node only if this link is not yet
        defined.  This used when the entire document is completed and
        the missing links are filled in.
        """

        # check the link is of a valid type
        if link not in _NODE_LINK_TYPES:
            return ValueError(f"node: @{self.name} set default invalid link"
                              f" type: {link}")

        if target:
            self._links.setdefault(link, target)


    def getlink(self, link):
        """Return the link to the specified target from this node, or
        None, if it is not defined.
        """

        # check the link is of a valid type
        if link not in _NODE_LINK_TYPES:
            return ValueError(f"node: @{self.name} get invalid link type:"
                              f" {link}")

        return self._links.get(link)


    def addwarning(self, warning):
        """Add a warning to the list of warnings about this node.
        """

        self._warnings.append(warning)


    def getwarnings(self):
        """Return the list of warnings about this node.
        """

        return self._warnings


    def appendline(self, l):
        """Add a line to the current node.
        """

        self._lines.append(l)


    def parseindex(self):
        """Parse this node as an index, returning a GuideIndex() object
        with all the terms and references.
        """

        # initialise the index
        index = GuideIndex()

        # initialise the previous term found to 'not found yet'
        prev_term = None

        for line in self._lines:
            # parse this line and get the term used in it (or the
            # previous one, if one was not found, as this is continuing
            # that)
            term = index.parseline(line, prev_term)

            # store this term as the previous one
            prev_term = term

        return index


    def write(self, *, doc_name=None, node_docs={}, line_maxlen=80):
        # the current line being assembled
        line_markup = ""
        line_render = ""

        # any spaces
        pre_space = ""

        word_markup = ""
        word_render = ""


        # formatted lines in the output
        output = ["@node " + self.name]

        for link in _NODE_LINK_TYPES:
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
            if (len(line_render + pre_space + word_render) > line_maxlen):
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
