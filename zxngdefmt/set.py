# zxngdefmt/set.py

# Sets are groups of documents (files) which are processed together,
# with links between them and some other shared elements, such as index
# nodes.



import sys

from .index import GuideIndex
from .node import GuideNodeDocs, LINE_MAXLEN
from .doc import GuideDoc



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

        # copy our list of set-level warnings as we want to extend and
        # then return it, but not affect the original list
        warnings = self._warnings.copy()

        # extend the list of warnings with those from each document
        for doc in self._docs:
            warnings.extend([ f"document: {doc.getname()} {warning}"
                                  for warning in doc.getwarnings() ])

        # return the composite list of warnings
        return warnings


    def makecommonindex(self, line_maxlen=LINE_MAXLEN):
        """Make an consolidated index for the set, merging together the
        indices in each document.
        """

        # initialise an empty index then merge each document's index
        # into it, creating a consolidated ones
        self.index = GuideIndex()
        for doc in self._docs:
            self.index.merge(doc.index)

        # render out the consolidated index to a list of formatted lines
        common_index_lines = self.index.format(line_maxlen)

        # replace the index node's lines in each document in the set
        # with the consolidated version
        #
        # TODO - warnings when index page is missing or different node
        for doc in self._docs:
            index_node = doc.getindexnode()
            if index_node:
                index_node.replacelines(common_index_lines)


    def print(self):
        for doc in self._docs:
            print(f"=> DOC: {doc.getname()}")
            print('\n'.join(doc.format(node_docs=self._node_docs)))
