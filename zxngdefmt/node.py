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



# maximum rendered length for a single line in a formatted the output guide

LINE_MAXLEN = 80


# valid types of links from a node

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

        # initialise the links to other nodes (prev/next/toc)
        self._links = {}

        # initialise list of warnings encountered
        self._warnings = []


    def __repr__(self):
        return f"GuideNode(@{self.name})"


    def setlink(self, type_, target):
        """Unconditionally set the link to another node (prev/next/toc).
        This is used when a node explicitly sets the link.
        """

        # check the link is of a valid type
        if type_ not in _NODE_LINK_TYPES:
            return ValueError(
                f"node: @{self.name} set invalid link type: {type_}")

        self._links[type_] = target


    def setdefaultlink(self, type_, target):
        """Set the link to another node only if this link is not yet
        defined.  This used when the entire document is completed and
        the missing links are filled in.
        """

        # check the link is of a valid type
        if type_ not in _NODE_LINK_TYPES:
            return ValueError(
                f"node: @{self.name} set default invalid link type:"
                f" {type_}")

        if target:
            self._links.setdefault(type_, target)


    def getlink(self, type_):
        """Return the link to the specified target from this node, or
        None, if it is not defined.
        """

        # check the link is of a valid type
        if type_ not in _NODE_LINK_TYPES:
            return ValueError(
                f"node: @{self.name} get invalid link type: {type_}")

        return self._links.get(type_)


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


    def checklink(self, link_type, node_names):
        """Check the target of a particular node link type exists in the
        supplied list of node names (from a document or set), returning
        False iff it is defined and does not.

        A warning will also be recorded, if it does not.
        """

        link_name = self.getlink(link_type)

        # if link is defined and no node exists with that name,
        # record a warning
        exists = (not link_name) or (link_name in node_names)
        if not exists:
            self.addwarning(
                f"link type: {link_type} to non-existent node: @{link_name}")

        return exists


    def checklinks(self, node_names):
        """Check all the node link types for this document exist in the
        supplied list of node names (from a document or set).  False
        will be returned iff any are defined and are missing, as well as
        warnings recorded.
        """

        all_exist = True
        for link_type in _NODE_LINK_TYPES:
            all_exist &= self.checklink(link_type, node_names)

        return all_exist


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

            # store the term from this line (or continued from a
            # previous line) as the new previous one
            prev_term = term

        return index


    def format(self, *, doc_name=None, node_docs={}, line_maxlen=80):
        """Return the node as a list of lines of markup, formatted with
        word wrap for the specified maximum line length.
        """


        # the list of output lines to be returned, starting with the
        # '@node' command, identifying the node
        output = ["@node " + self.name]

        # the current line being assembled - we store two versions:
        #
        # line_markup contains the text containing literal text and
        # commands and is used for the actual output
        line_markup = ""
        #
        # line_render contains the displayed text equivalent, obtained
        # using rendertoken(), and is used to calculate displayed text
        # lengths for wrapping words
        line_render = ""

        # the current 'word' being assembled - a word is a sequence of
        # tokens (markup, literal text, etc.) that cannot be broken
        # across lines - if it cannot fit on a line, a new line will be
        # begun
        word_markup = ""
        word_render = ""

        # any spaces before the current word - these will be discarded
        # if the word wraps onto the next line
        pre_space = ""

        # add the links to other documents (prev/next/toc)
        for link in _NODE_LINK_TYPES:
            if link in self._links:
                output.append(f"@{link} {self._links[link]}")


        # --- subfunctions ---


        def writeline():
            """Add the line currently being assembled to the list of
            output lines and start a new one.
            """

            nonlocal line_markup, line_render, pre_space

            if line_markup:
                output.append(line_markup)

                line_markup = ''
                line_render = ''

                # as we're starting a new line, we don't need the spaces
                # that would separate the current word from the previous
                # one
                pre_space = ''


        def completeword(space=''):
            """Called when the current word being assembled has been
            completed (by some space, or at the end of a document).  It
            will add the word to the end of the line, if it fits, or
            start a new one with it.

            The supplied 'space' is the separator between this complete
            word and the next and is recorded in pre_space.
            """

            nonlocal line_markup, line_render, word_markup, word_render
            nonlocal pre_space

            # if no line or word is currently being assembled, we have
            # nothing to do
            if (not line_render) and (not word_render):
                return

            # check if adding the pre_space and word to the line would
            # take it over the maximum length
            if len(line_render + pre_space + word_render) > line_maxlen:
                # line would be over maximum - write it out
                writeline()

                # discard the space, as we're beginning a new line

            else:
                # the word will fit on this line - add the separating
                # pre_space
                line_markup += pre_space
                line_render += pre_space

            # add the word to the line (either a new, empty one, or
            # continuing the current one)
            line_markup += word_markup
            line_render += word_render

            # start a new word
            word_markup = ''
            word_render = ''

            # record the supplied space if required for the next word
            pre_space = space


        def appendtoken(token):
            """Add the supplied token to the current word.
            """

            nonlocal word_markup, word_render

            word_markup += token
            word_render += rendertoken(token)


        def fixlink_repl(m):
            """Used as an argument to re.sub(repl) to fix up links, if
            required; qualifying them with the document name, if they
            are in a different document to the this node.

            This function uses the doc_name and node_docs arguments to
            the containing format() method.
            """

            text, target = m.group("link_text", "link_target")

            # fix up the target - if not found in node_docs, None will
            # be returned
            fixed_target = node_docs.fixlink(doc_name, target)

            # if the target was not found, record a warning
            if fixed_target is None:
                self._warnings.append(f"link: {text} target: @{target}"
                                      "does not exist")

            # return the fixed link or, if the target was not found,
            # return the target anyway
            return '@{"' + text + '" LINK ' + (fixed_target or target) + '}'


        # --- method ---


        # go through the lines in this node
        for line in self._lines:
            # fix all the links in this line such that, if a link is to
            # a node in another document in the set, qualify it by
            # prefixing 'Document/'
            #
            # this will also record warnings on for link targets which
            # don't exist
            line = re.sub(LINK_RE, fixlink_repl, line)

            # if the line is blank, or is one that is to be included
            # literally, just add that to the document
            if (line == '') or LITERALLINE_RE.match(line):
                # finish the current line and append it (if it has
                # something in it)
                writeline()

                # add the literal line
                output.append(line)

                continue

            # go through the line matching tokens (markup, literal or spaces)
            remainder = line
            while remainder:
                m = re.match(TOKEN_RE, remainder)

                # if we couldn't match a token, something has gone
                # irretrievably wrong (probably with the regexp)
                if not m:
                    raise ValueError(
                              "failed to match next token in: " + remainder)

                token, remainder = m.group("token", "remainder")

                if m.group("space"):
                    # token is a space - complete the current word
                    completeword(space=token)
                else:
                    # token is not a space - try to add it to the
                    # current line (otherwise begin a new one)
                    appendtoken(token)

            # the end of line in the source text completes a word and
            # adds a separating space before the next one (if there is
            # one)
            completeword(space=' ')

        # we've finished the node, flush out anything assembled in the
        # line buffer
        writeline()

        # return the list of formatted lines
        return output
