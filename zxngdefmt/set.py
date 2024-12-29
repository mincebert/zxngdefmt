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


    def getwarnings(self):
        """Return all the warnings from the set.

        This will include set-level warnings, as well as warnings from
        all the documents in it (which will include those from nodes
        within them).
        """

        # initialise the list of warnings (there aren't any at the set
        # level yet, so we just use an empty list)
        warnings = []

        # extend the list of warnings with those from each document
        for doc in self._docs:
            warnings.extend([ f"document: {doc.getname()} {warning}"
                                  for warning in doc.getwarnings() ])

        # return the composite list of warnings
        return warnings


    def makeindex(self):
        """Make an overall index for the set, merging together the
        index in each document.
        """

        # initialise an empty index
        self.index = GuideIndex()

        # go through each document in the set, merging their index into
        # the set one
        for doc in self._docs:
            self.index.merge(doc.index)


    def formatindex(self, line_maxlen=LINE_MAXLEN):
        for doc in self._docs:
            return self.index.format(doc.getname(), self._node_docs, line_maxlen)


    def print(self):
        for doc in self._docs:
            print(f"=> DOC: {doc.getname()}")
            print('\n'.join(doc.format(node_docs=self._node_docs)))
