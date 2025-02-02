# zxngdefmt/doc.py

# Documents are NextGuide files containing one or more nodes.



import os
import re

from .index import GuideIndex
from .node import GuideNode, LINE_MAXLEN

from .token import (
    IGNORE_RE,
    NODE_LINK_CMDS_RE,
    NODE_CMDS_RE,
)



# --- constants ---



# DOCCMD_x = string
#
# Constants identifying document commands.

DOC_CMD_INDEX = "index"



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
    DOC_CMD_INDEX,
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


    def __init__(self, filename, *, subindex_names=set()):
        """Initialise a new document, reading in data from a file.
        """

        super().__init__()

        # --- set up initial variables ---

        # store the name and subindex node names of this document
        self._setname(filename)

        # initialise the list of index node names to the subindex set;
        # when we read the file in later, we'll also add on the node
        # named in the '@index' command, if there is one
        self._index_names = set(subindex_names)

        # initialise document-level commands as empty
        self._cmds = {}

        # initialise the list of nodes as empty
        self._nodes = []

        # initialise an empty dictionary of indices - this will be
        # populated by parseindices(), if called
        self._indices = {}

        # initialise a list of warnings encountered when processing this
        # document
        self._warnings = []

        # --- read and process the document ---

        # read in the document file
        self.readfile(filename)

        # check the links to make sure they're not broken - we do this
        # here, before we set the default links, as we don't want to
        # report on broken links we fill in automatically; only the ones
        # supplied in the source file (to help the user find the initial
        # location of the problem)
        self.checklinks()

        # set the default links between nodes and to the contents node
        self.setdefaultlinks()


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


    def getcmd(self, name):
        """Get the value of a document level command.  If the command is
        not specified, None will be returned.
        """

        return self._cmds.get(name)


    def getnodenames(self):
        """Return a list containing the names of all the nodes in the
        document in order.
        """

        return [ node.name for node in self._nodes ]


    def getnode(self, name):
        """Return the node of the specified name.  If the node doesn't
        exist, None will be returned.
        """

        for node in self._nodes:
            if node.name == name:
                return node

        return None


    def getindices(self):
        """Get the list of index names.
        """

        return list(self._indices)


    def getindex(self, name):
        """Get the index under the specified name.
        """

        return self._indices[name]


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
        for index in self._indices:
            warnings.extend(
                [ f"index: {warning}"
                      for warning in self._indices[index].getwarnings() ])

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

                # anything else is a line of markup data in the node ...

                # we haven't started a node yet so we can't store this
                # line - add a warning and skip the line
                if not current_node:
                    self.addwarning(f"node data: '{l} outside node - ignoring")
                    continue

                # add this line to the current node
                current_node.appendline(l)

        # we're finished with the file - if we have a node we're
        # assembling, that's complete, so append that to list of nodes
        # in this document
        if current_node:
            self._nodes.append(current_node)

        # if the document had an index named in the '@index' document
        # command, add that to the list of index node names
        doc_index_name = self._cmds.get(DOC_CMD_INDEX)
        if doc_index_name:
            self._index_names.add(doc_index_name)


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
        index_name = self._cmds.get(DOC_CMD_INDEX)
        if index_name and (index_name not in node_names):
            self.addwarning(f"index node: @{index_name} does not exist")

        # check node-level links for all nodes in the document
        for node in self._nodes:
            node.checklinks(node_names)


    def parseindices(self):
        """Parse the index nodes of the document, if it is defined and
        exists, into a GuideIndex.  The index is stored in .index and
        True returned; if the node was not defined, or defined but not
        present, None is returned.
        """

        # --- make the list indices for this document ---

        # initialise the list of index names to empty
        index_names = []

        # if the document has an '@index' then add that as the first index
        index_name = self.getcmd(DOC_CMD_INDEX)
        if index_name:
            index_names.append(index_name)

        # add any additional subindex names supplied to this function
        index_names.extend(i for i in self._index_names if i != index_name)

        # --- process the indices ---

        # initialise the index as empty
        self._indices = {}

        # go through the list of indices we built above
        for index_name in index_names:
            # try to get the node with the same name as the index
            index_node = self.getnode(index_name)

            # if it exists - parse the node as an index and store the
            # returned GuideIndex in the document
            if index_node:
                self._indices[index_name] = index_node.parseindex()


    def format(self, *, node_docs={}, line_maxlen=LINE_MAXLEN, markup=True,
               skip_index=False):

        """Format the document for output, with the document commands
        first, then the nodes, handling word wrap for the specified
        specified maximum line length, and qualifying links with
        document names, if required.

        The output is returned as a list of lines as strings.

        Keyword arguments:

        line_maxlen -- the maximum line length; lines longer than this
        will be word-wrapped (unless matching the 'literal' format).

        markup -- if not set, a readable, plain text version without
        markup, will be generated.

        skip_index -- will omit index nodes in the output.
        """

        # initialise the output as an empty list of lines
        output = []

        # go through the document commands and record them in the
        # output, if they are present and not the empty string or None
        if markup:
            for cmd in DOC_CMDS:
                if cmd in self._cmds:
                    output.append(f"@{cmd} {self._cmds[cmd]}")

        # go through the nodes in the document in order
        for node in self._nodes:
            # if the name of this node is in the list of indices for
            # this document, and we're skipping those, ignore this node
            if skip_index and (node.name in self.getindices()):
                continue

            # add a line of dashes before this node as a separator
            if markup:
                output.append('@' + ('-' * (line_maxlen - 1)))
            else:
                node_banner = "---[ " + node.name + " ]"
                node_banner += '-' * (line_maxlen - len(node_banner) - 1)

                output.extend(['', node_banner, ''])

            # format this node and add the lines to the output
            output.extend(node.format(doc=self, node_docs=node_docs,
                                      line_maxlen=LINE_MAXLEN, markup=markup))

        # return the list of formatted lines
        return output
