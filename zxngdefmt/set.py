# zxngdefmt/set.py

# Sets are groups of documents (files) which are processed together,
# with links between them and some other shared elements, such as index
# nodes.



import os

from .link import GuideNodeDocs, GuideIndex
from .node import GuideNode, LINE_MAXLEN
from .doc import GuideDoc, DOC_MAXSIZE



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

        # initialise an empty dictionary of indices - this will be keyed
        # on the node name of the index, as they are parsed, allowing
        # multiple indices to be stored
        self._indices = {}

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

            # add the index node to the set of 'always local' nodes
            index_node = doc.getindexnode()
            if index_node:
                self._node_docs.addcommonnode(index_node.name)

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

                # add a warning if this file is over the maximum size
                # for a single NextGuide document
                if f.tell() > DOC_MAXSIZE:
                    doc.addwarning(f"over maximum size ({DOC_MAXSIZE} bytes)")


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

        # add in the warnings from the set indices
        for index in sorted(self._indices):
            warnings.extend(
                [ f"set index: {index} {warning}"
                    for warning in self._indices[index].getwarnings() ])

        # return the composite list of warnings
        return warnings


    def getnodedocs(self):
        """Return a dictionary keyed on the name of all nodes in the
        set, with the values as a list of the documents in which that
        node is defined.
        """

        nodes = {}
        for doc in self._docs:
            for node_name in doc.getnodenames():
                nodes.setdefault(node_name, []).append(doc.getname())
        return nodes


    def makeindices(self, line_maxlen=LINE_MAXLEN):
        """Make an consolidated indices for the set, merging together
        the index pages with the same node name as each other.

        This means that all index nodes which have the same name will
        have the same entries across the set.  If a document has a
        differently-named index node, however, it will be kept separate
        (unless other documents have an index node with the same name,
        then just those will be merged).
        """


        # initialise an empty set of indices as a dictionary
        #
        # the dictionary will be keyed off each index node name across
        # the set
        self._indices = {}


        # go through the documents in the set, building the consolidated
        # indices
        for doc in self._docs:
            # get the name of this document's index node
            doc_index_name = doc.getindexnode().name

            # skip this document, if it doesn't have an index
            if not doc_index_name:
                continue

            # if we haven't already started an index with the same name
            # as this document's index node, create one now
            if doc_index_name not in self._indices:
                self._indices[doc_index_name] = GuideIndex()

            # merge this document's index into the consolidated one
            # under the same name
            self._indices[doc_index_name].merge(doc.getindex())


        # create a dictionary of formatted indices (keyed off the index
        # node name)
        formatted_indices = {
            index_name: self._indices[index_name].format(line_maxlen)
                for index_name in self._indices }


        # go through the documents in the set, fixing up the indices
        for doc in self._docs:
            # get this document's index node (or None, if there isn't one)
            index_node = doc.getindexnode()

            # skip this document, if it doesn't have an index
            if not index_node:
                continue

            # replace the lines in the node (either existing, or new)
            # with the set index, sandwiched between the header and
            # footer lines from the index node in this document, and
            # separator blank lines
            index_node.replacelines(
                doc.getindex().header
                + ['']
                + formatted_indices[index_node.name]
                + ['']
                + doc.getindex().footer)
