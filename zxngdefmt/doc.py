# zxngdefmt/doc.py

# Documents are NextGuide files containing one or more nodes.



import os
import re

from .link import GuideIndex
from .node import GuideNode, LINE_MAXLEN

from .token import (
    IGNORE_RE,
    NODE_LINK_CMDS_RE,
    NODE_CMDS_RE,
)



# --- constants ---



# DOC_CMDS = list
#
# This defines the available commands at the document (file) level.
# They are used to construct a regular expression to match lines
# containing them.
#
# In addition, the order of this list determines the order in which they
# are included in the output document file.

DOC_CMDS = [
    "title",
    "author",
    "copyright",
    "version",
    "date",
    "build",
    "index",
]


# regular expression to match document-level commands

DOC_CMDS_RE = re.compile(
                  r"@(?P<cmd>" + '|'.join(DOC_CMDS) + r")( (?P<value>.+))?")


# maximum size of a document in bytes

DOC_MAXSIZE = 65_535



# --- classes ---



class GuideDoc(object):
    """Class representing a NextGuide document, which is a single file
    containing one or more nodes (pages).
    """


    def __init__(self, filename):
        """Initialise a new document, reading in data from a file.
        """

        super().__init__()

        # store the name of this document from the filename
        self._setname(filename)

        # initialise document-level commands
        self._cmds = {}

        # initialise the list of nodes
        self._nodes = []

        # initialise an empty index - if one is requested to be built,
        # this will be replaced with a completed one
        self._index = GuideIndex()

        # initialise a list of warnings encountered when processing this
        # document
        self._warnings = []

        # read the file, set the default links and check it
        self.readfile(filename)
        self.checklinks()
        self.setdefaultlinks()
        self.parseindex()


    def _setname(self, name):
        """Sets the name of the guide.  This will 'normalise' the
        supplied name, removing '.gde' from the end, if it is present;
        if not, the complete name will be stored.
        """

        # get the leaf part of the name
        basename = os.path.basename(name)

        # strip off '.gde' if that's present (the NextGuide viewer will
        # add that on, if the file is not found, with the plain name)
        if basename.endswith(".gde"):
            self._name = basename[:-4]
        else:
            self._name = basename


    def getname(self):
        """Return the name of the guide.  This can be used as the
        document name when making links from other guide documents.
        """

        return self._name


    def getnode(self, name):
        """Return the node of the specified name.  If the node doesn't
        exist, None will be returned.
        """

        for node in self._nodes:
            if node.name == name:
                return node

        return None


    def getnodenames(self):
        """Return a list containing the names of all the nodes in the
        document in order.
        """

        return [ node.name for node in self._nodes ]


    def getindex(self):
        """Get the index.
        """

        return self._index


    def setindexnode(self, node):
        """Set the node used as the index for this document.  The node
        is supplied as a GuideNode object and the 'index' document-level
        command is set to use this node.

        If a node with the same name already exists, ValueError
        exception is raised.
        """

        if self.getnode(node.name):
            raise ValueError(f"node with name: {node.name} already"
                             " exists in document")

        # add the node to the document and set the index command to
        # point to it
        self._nodes.append(node)
        self._cmds["index"] = node.name


    def getindexnode(self):
        """Get the GuideNode object repesenting the index for this
        document.  If the node is not defined, or does not exist, None
        is returned.
        """

        return self.getnode(self._cmds.get("index"))


    def addwarning(self, warning):
        """Add a warning to the list of warnings about this document.
        """

        self._warnings.append(warning)


    def getwarnings(self):
        """Returns the list of warnings encountered when building the
        document.  This will include document-level warnings, as well as
        warnings from all nodes in the document.

        If there are no warnings, an empty list will be returned.
        """

        # copy our list of document-level warnings as we want to extend
        # and then return it, but not affect the original list
        warnings = self._warnings.copy()

        # add warnings from the index, prefixed with 'index:'
        warnings.extend(
            [ "index: " + warning for warning in self._index.getwarnings() ])

        # extend the copied list with the warnings from each node in the
        # document, prefixed by 'node: @name'
        for node in self._nodes:
            warnings.extend([ f"node: @{node.name} {warning}"
                                  for warning in node.getwarnings() ])

        # return the composite list of warnings
        return warnings


    def readfile(self, filename):
        """Read a source NextGuide file, parsing document-level comamnds
        and nodes and storing it as this document.
        """

        # start with no current node
        current_node = None

        # open the source file and work through the lines in it
        with open(filename) as f:
            for l in f:
                # strip any trailing whitespace as we never want that
                l = l.rstrip()

                # skip lines we want to ignore
                if IGNORE_RE.match(l):
                    continue

                # match document-level commands
                m = DOC_CMDS_RE.match(l)
                if m:
                    if current_node:
                        # we got a document-level command but are in a
                        # node - record a warning and ignore it
                        current_node.addwarning(
                            f"document token: '{l}' in node - ignored")

                    else:
                        # we're not in a node, record the command in the
                        # document
                        self._cmds[m.group("cmd")] = m.group("value")

                    # skip to the next line in the file
                    continue

                # try to match the @node command at the start of a new node
                m = NODE_CMDS_RE.match(l)
                if m:
                    # if we've got a node we're building, we're done
                    # with that, so append it to the list of nodes in
                    # this document
                    if current_node:
                        self._nodes.append(current_node)

                    # start a new node
                    current_node = GuideNode(m.group("name"))

                    # skip to the next line in the file
                    continue

                # try to match node-level commands linking to another node
                m = NODE_LINK_CMDS_RE.match(l)
                if m:
                    # store the link and skip to the next line in the file
                    current_node.setlink(*m.group("link", "name"))
                    continue

                # anything else is a line of markup data in the node -
                # we just store that as is and format it when required
                current_node.appendline(l)

        # we're finished with the file - if we have a node we're
        # assembling, append that to list of nodes in this document
        if current_node:
            self._nodes.append(current_node)


    def setdefaultlinks(self):
        """Complete any missing inter-node links using some assumed
        defaults:

        prev = the previous node in the document

        next = the next node in the document

        toc = the most recently-defined 'toc' entry
        """


        # work through the nodes in order, filling in missing 'prev' and
        # 'toc' links from the previous node

        prev_node = None
        toc_node = None

        for node in self._nodes:
            # set missing links for this node
            node.setdefaultlink("prev", prev_node)
            node.setdefaultlink("toc", toc_node)

            # the default previous link for the next one is this node
            prev_node = node.name

            # the default toc link is the one we used for this node
            # (which may have been explicitly specified, or set the same
            # as the previous node)
            toc_node = node.getlink("toc")


        # work through the nodes in REVERSE order, filling in the 'next'
        # link from the next node

        next_node = None

        for node in reversed(self._nodes):
            node.setdefaultlink("next", next_node)
            next_node = node.name


    def checklinks(self):
        """Check links in the document and generate warnings if any are
        broken (to nodes which do not exist).
        """

        # get the list of node names as we're going to use it several
        # times
        node_names = self.getnodenames()

        # record a warning if the index node is defined but does not exist
        index_name = self._cmds.get("index")
        if index_name and (index_name not in node_names):
            self.addwarning(f"index node: @{index_name} does not exist")

        # check node-level links for all nodes in the document
        for node in self._nodes:
            node.checklinks(node_names)


    def parseindex(self):
        """Parse the index node of the document, if it is defined and
        exists, into a GuideIndex.  The index is stored in .index and
        True returned; if the node was not defined, or defined but not
        present, None is returned.
        """

        # initialise the index as empty
        self._index = GuideIndex()

        # get the index node defined for this document - if one was not
        # defined or the node defined was not found, return None to
        # indicate no index node was processed
        #
        # we don't add a warning if the node was not persent as this
        # would be done by checklinks()
        index_node = self.getindexnode()
        if not index_node:
            return None

        # parse the node as an index and store the returned GuideIndex
        # in the document
        self._index = index_node.parseindex()

        # return success
        return True


    def format(self, *, node_docs={}, line_maxlen=LINE_MAXLEN):
        """Format the document for output, with the document commands
        first, then the nodes, handling word wrap for the specified
        specified maximum line length, and qualifying links with
        document names, if required.

        The output is returned as a list of lines as strings.
        """

        # initialise the output as an empty list of lines
        output = []

        # go through the document commands and record them in the
        # output, if they are present
        for cmd in DOC_CMDS:
            if cmd in self._cmds:
                output.append(
                    f"@{cmd} {self._cmds[cmd]}" if cmd in self._cmds else '')

        # go through the nodes in the document in order
        for node in self._nodes:
            # add a line of dashes before this node as a separator
            output.append('@' + ('-' * (line_maxlen - 1)))

            # format this node and add the lines to the output
            output.extend(node.format(doc_name=self.getname(),
                                      node_docs=node_docs,
                                      line_maxlen=LINE_MAXLEN))

        # return the list of formatted lines
        return output
