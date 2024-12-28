# zxngdefmt/set.py



import sys

from .index import GuideIndex
from .node import GuideNodeDocs
from .doc import GuideDoc



class GuideSet(object):
    """Handles a set of GuideDocs with interconnecting links.

    TODO
    """

    def __init__(self, filenames):
        super().__init__()

        # initialise a list of documents in the set
        self._docs = []

        # initialise a dictionary mapping nodes to docs
        self._node_docs = GuideNodeDocs()

        # initialise list of warnings at the set level (warnings from
        # individual documents are stored there and concatenated, when
        # requests by getwarnings())
        self._warnings = []

        self.readfiles(filenames)


    def readfiles(self, filenames):
        # go through the list of filenames and read a document from each one
        for filename in filenames:
            doc = GuideDoc(filename)

            # add this document to the list of documents in the set
            self._docs.append(doc)

            # go through the nodes in this new document
            for node_name in doc.getnodenames():
                # if a node with this name already exists, record a
                # warning and skip adding it
                if node_name in self._node_docs:
                    self._warnings.append(
                        f"document: {doc.getname()} node:"
                        f" @{node_name} same name already exists in"
                        f" document: {self._node_docs[node_name]} -"
                        f" ignoring")
                    continue

                # record this node as in this document
                self._node_docs[node_name] = doc.getname()


    def getwarnings(self):
        """Return all the warnings from the set.

        This will include set-level warnings (e.g. a node name clashes
        between two documents).  It will also include all the
        document-level warnings, which will be prefixed with the name
        of the document.
        """

        warnings = self._warnings.copy()

        for doc in self._docs:
            warnings.extend([ f"document: {doc.getname()} {warning}"
                                  for warning in doc.getwarnings() ])

        return warnings


    def parseindex(self):
        self.index = GuideIndex()
        for doc in self._docs:
            doc.parseindex()
            print("DOC INDEX", doc.getname(), "INDEX=>", doc.index, file=sys.stderr)
            for term in doc.index:
                self.index.setdefault(term, {})
                self_term = self.index[term]
                self_term.setdefault("refs", {})
                doc_term = doc.index[term]
                if doc_term["target"]:
                    self_term["target"] = doc_term["target"]
                self_term["refs"].update(doc_term["refs"])


    def formatindex(self):
        return self.index.format()


    def print(self):
        for doc in self._docs:
            print(f"=> DOC: {doc.getname()}")
            doc.print(node_docs=self._node_docs)
