# zxngdefmt/set.py

# Sets are groups of documents (files) which are processed together,
# with links between them and some other shared elements, such as index
# nodes.



import os

from .link import GuideNodeDocs, GuideIndex
from .node import GuideNode, LINE_MAXLEN
from .doc import GuideDoc



# --- constants ---



# DEFAULT_INDEX_NAME = string
#
# The default name for an index node, if one is not defined.

DEFAULT_INDEX_NAME = "INDEX"



# --- classes ---



class GuideSet(object):
    """Handles a set of GuideDocs with interconnecting links and common
    index.
    """


    def __init__(self, filenames):
        """Initialise the set of documents by reading in the supplied
        files.
        """

        super().__init__()

        # initialise a list of documents in the set
        self._docs = []

        # initialise a dictionary mapping nodes to documents
        #
        # this is used to provide an overall list of all nodes, and to
        # qualify links with document names, when the link to nodes in
        # other documents
        self._node_docs = GuideNodeDocs()

        # initialise an empty index - if one is requested to be built,
        # this will be replaced with a completed one
        self._index = GuideIndex()

        # initialise the list of warnings at the set level to empty
        self._warnings = []

        # read in the document files in the set
        self.readfiles(filenames)


    def readfiles(self, filenames):
        """Read the list of document files into a set.
        """

        # go through the supplied list of filenames
        for filename in filenames:
            # read in that file and make a document
            doc = GuideDoc(filename)

            # add this document to the list of documents in the set
            self._docs.append(doc)

            # add the nodes in this document to the GuideNodeDocs
            # mapping object
            self._node_docs.addnodes(doc)


    def writefiles(self, dir):
        """Write out the set to a series of files in the specified
        directory.

        The filenames will be the document names with '.gde' suffixed.
        """

        for doc in self._docs:
            with (open(os.path.join(dir, doc.getname() + ".gde"), 'w')
                      as f):
                print('\n'.join(doc.format(node_docs=self._node_docs)),
                      file=f)


    def print(self):
        """Print out the set of guide documents to standard output, with
        a separator between each one.

        This is intended more as a debugging function rather than useful
        program operation.
        """

        for doc in self._docs:
            print()
            print(f"=== {doc.getname()} ===")
            print()
            print('\n'.join(doc.format(node_docs=self._node_docs)))


    def addwarning(self, warning):
        """Add a warning to the list of warnings about this set.
        """

        self._warnings.append(warning)


    def getwarnings(self):
        """Return all the warnings from the set.

        This will include set-level warnings, as well as warnings from
        all the documents in it (which will include those from nodes
        within them).
        """

        # start with an empty warnings list
        warnings = []

        # first, extend the list of warnings with those from each
        # document
        for doc in self._docs:
            warnings.extend([ f"document: {doc.getname()} {warning}"
                                  for warning in doc.getwarnings() ])

        # add in our warnings - we do this after the document ones as
        # these a generated after each document is processed
        warnings.extend(self._warnings)

        # add in the warnings from the common index
        warnings.extend(
            [ "set index: " + warning
                  for warning in self._index.getwarnings() ])

        # return the composite list of warnings
        return warnings


    def makecommonindex(self, line_maxlen=LINE_MAXLEN):
        """Make an consolidated index for the set, merging together the
        indices in each document, and replace the index node in each
        document with it (or add a new index node, if one does not
        exist).
        """

        # initialise an empty index then merge each document's index
        # into it, creating a consolidated ones
        self._index = GuideIndex()
        for doc in self._docs:
            self._index.merge(doc.getindex())

        # render out the consolidated index to a list of formatted lines
        common_index_lines = self._index.format(line_maxlen)

        # initialise the common index node name to undefined - we'll set
        # this to the name used in the first document in the set (or
        # pick a sensible default)
        common_index_name = None

        # work through the documents in the set, replacing (or adding)
        # the index node with the consolidated version
        for doc in self._docs:
            # get the current index node (or None, if there isn't one)
            index_node = doc.getindexnode()

            # if we haven't got a common index node name yet (which
            # means we're processing the first document in the set),
            # we need to set that somehow ...
            if not common_index_name:
                if index_node:
                    # we have an index node in this document - use the
                    # name from that
                    common_index_name = index_node.name

                else:
                    # we DON'T have an index node defined for this
                    # document - use a default and add a warning

                    common_index_name = DEFAULT_INDEX_NAME

                    self.addwarning(
                        "no index node defined in first document of a"
                        f"set - assuming default: @{common_index_name}")


            # if this document doesn't have an index node, we need to
            # create one and will use the common (first or default) name
            # for it ...
            if not index_node:
                existing_node = doc.getnode(common_index_name)

                if existing_node:
                    # we have an existing node with the common name -
                    # add a warning and use it, which will replace its
                    # contents with our common index

                    existing_node.addwarning(
                        "existing node's name clashes with common"
                        " index name - replacing contents of possible"
                        " non-index node")

                    index_node = existing_node

                else:
                    # we DON'T have an existing node with the common
                    # name - create a new node with that name, add it
                    # to the document and set it as the index node
                    # (we'll fill in the content later)
                    if not index_node:
                        index_node = GuideNode(common_index_name)
                        doc.setindexnode(index_node)

            # we do have an existing index node - check if its name is
            # different from the common name and add a warning if so
            elif index_node.name != common_index_name:
                doc.addwarning(f"index node: @{index_node.name} is"
                                " inconsistent with common index node"
                                f" name: @{common_index_name}")

            # replace the lines in the node (either existing, or new)
            # with the common index
            index_node.replacelines(common_index_lines)
