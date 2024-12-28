# zxngdefmt/doc.py



import re
import sys

from .node import GuideNode

from .token import (
    IGNORE_RE,
    NODAL_CMDS_RE,
    NODE_CMDS_RE
)



# document-level commands
#
# This defines the order in which the commands are written in an output
# guide, as well as to construct the regular expression of commands to
# match.

DOC_CMDS = [
    "title",
    "author",
    "copyright",
    "version",
    "date",
    "build",
    "index",
]


# matching document-level tokens
DOC_CMDS_RE = (r"@(?P<cmd>" + '|'.join(DOC_CMDS) + r")( (?P<value>.+))?")


# maximum length for a single line in the output guide

LINE_MAXLEN = 80



class GuideDoc(object):
    """Class representing an entire NextGuide document.

    TODO
    """


    def __init__(self, filename):
        """Initialise a new raw document object, optionally reading in a
        source guide file.
        """

        super().__init__()

        # initialise the document
        self._cmds = {}
        self._nodes = []

        # initialise a list of warnings encountered when building the
        # document
        self._warnings = []

        # store the name of this document
        self.setname(filename)

        # read the file, set the default links and check it
        self.readfile(filename)
        self.checklinks()
        self.setdefaultlinks()
        self.parseindex()


    def setname(self, name):
        """Sets the name of the guide.  This will 'normalise' the
        supplied name, removing '.gde' from the end, if it is present;
        if not, the complete name will be stored.
        """

        if name.endswith(".gde"):
            self._name = name[:-4]
        else:
            self._name = name


    def getname(self):
        """Return the name of the guide for use as the document part of
        links from other guides.
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
        """Read a source NextGuide file and store it as a raw document.

        TODO
        """


        current_node = None

        with open(filename) as f:
            for l in f:
                # strip any trailing whitespace
                l = l.rstrip()

                # skip lines we want to ignore
                if re.match(IGNORE_RE, l):
                    continue

                # match document-level commands
                m = re.match(DOC_CMDS_RE, l)
                if m:
                    if not current_node:
                        self._cmds[m.group("cmd")] = m.group("value")
                    else:
                        current_node.addwarning(
                            f"document token: '{l}' in node - ignored")

                    continue

                # match the start of a new node
                m = re.match(NODE_CMDS_RE, l)
                if m:
                    # append the current node, if we have one
                    if current_node:
                        self._nodes.append(current_node)

                    # start a new node
                    current_node = GuideNode(m.group("name"))
                    continue

                # match node-level commands
                m = re.match(NODAL_CMDS_RE, l)
                if m:
                    current_node.setlink(*m.group("link", "name"))
                    continue

                # anything else is a line of markup data in the node
                current_node.appendline(l)

        # if we have a node we're assembling, append that
        if current_node:
            self._nodes.append(current_node)


    def setdefaultlinks(self):
        """Complete any missing data for inter-node links using
        defaults:

        - prev = the previous node in the document

        - next = the next node in the document

        - toc = the most recently-defined 'toc' entry
        """

        # fill in missing 'previous' and 'toc' (contents) links:
        prev_node = None
        toc_node = None
        for node in self._nodes:
            # set missing links for this node
            node.setdefaultlink("prev", prev_node)
            node.setdefaultlink("toc", toc_node)

            # store the information about this node to use in subsequent
            # ones, if required
            prev_node = node.name
            toc_node = node.getlink("toc")

        # fill in missing 'next' links
        next_node = None
        for node in reversed(self._nodes):
            node.setdefaultlink("next", next_node)
            next_node = node.name


    def checklinks(self):
        """Check links in the document and generate warnings if any are
        broken (to nodes which do not exist).
        """

        def checknodallink(link):
            """Check a particular nodal link exists.
            """

            link_name = node.getlink(link)
            if (link_name
                and all(node.name != link_name for node in self._nodes)):

                self._warnings.append(
                    f"node: @{node.name} link: {link} to non-existent"
                    f" node: @{link_name}")

        # check document-level links
        index = self._cmds.get("index")
        if index and all(node.name != index for node in self._nodes):
            self._warnings.append(f"index link to non-existent node: @{index}")

        # check node-level links
        for node in self._nodes:
            checknodallink("prev")
            checknodallink("next")
            checknodallink("toc")


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
            print('@' + ('-' * (LINE_MAXLEN - 1)))
            for l in n.write(doc_name=self.getname(), node_docs=node_docs):
                print(l)
