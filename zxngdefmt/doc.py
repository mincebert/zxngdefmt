# zxngdefmt/doc.py

# Documents are NextGuide files containing one or more nodes.



import re
import sys

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

        if name.endswith(".gde"):
            self._name = name[:-4]
        else:
            self._name = name


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

                    # start a new node and skip to the next line in the file
                    current_node = GuideNode(m.group("name"))
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
            self._warnings.append(
                f"index link to non-existent node: @{index_name}")

        # check node-level links for all nodes in the document
        for node in self._nodes:
            node.checklinks(node_names)


    def getnodenames(self):
        """Return a list containing the names of all the nodes in the
        document.
        """

        return [ node.name for node in self._nodes ]


    def getwarnings(self):
        """Returns the list of warnings encountered when building the
        document.  The list will be empty if there were no warnings.
        """

        warnings = self._warnings.copy()

        for node in self._nodes:
            warnings.extend([ f"node: @{node.name} {warning}"
                                  for warning in node.getwarnings() ])

        return warnings


    def parseindex(self):
        """Parse the index node of the document, if it exists.

        TODO
        """

        self.index = {}

        index_name = self._cmds.get("index")
        if not index_name:
            return

        print("IndexName", index_name, file=sys.stderr)
        index_node = self.getnode(index_name)

        if index_node:
            self.index = index_node.parseindex()

        print(self.index, file=sys.stderr)


    def print(self, *, node_docs={}):
        """TODO - just print the document and nodes raw
        """

        for c in DOC_CMDS:
            if c in self._cmds:
                print(f"@{c}"
                      + (f" {self._cmds[c]}" if c in self._cmds else ""))

        for n in self._nodes:
            print()
            print('@' + ('-' * (80 - 1)))
            for l in n.format(doc_name=self.getname(), node_docs=node_docs, line_maxlen=LINE_MAXLEN):
                print(l)
