# zxngdefmt/set.py

# Sets are groups of documents (files) which are processed together,
# with links between them and some other shared elements, such as index
# nodes.



import os

from .index import GuideNodeDocs, GuideIndex
from .node import LINE_MAXLEN
from .doc import GuideDoc, DOC_CMD_INDEX, DOC_MAXSIZE



# --- constants ---



# DEFAULT_INDEX_NAME = string
#
# The default name for an index node, if one is not defined.

DEFAULT_INDEX_NAME = "INDEX"



# --- functions ---



def _identity(i):
    """Simple identity function which returns the single argument it is
    passed.  It is used as the default for the 'indextermkey' argument
    in GuideSet.makeindices().
    """

    return i



# --- classes ---



class GuideSet(object):
    """Handles a set of GuideDocs with interconnecting links and common
    index.
    """


    def __init__(self, filenames, *, subindex_names=set()):
        """Initialise the set of documents by reading in the supplied
        list of filenames.

        Keyword arguments:

        subindex_names -- a list of node names which will also be
        treated as index nodes and combined across the set; this is
        useful if there are additional nodes acting as indices, separate
        from the one named with the '@index' document command.
        """

        super().__init__()

        # initialise a list of documents in the set as empty
        self._docs = []

        # initialise an empty dictionary of indices - this will be keyed
        # on the node name of the index, as they are parsed, allowing
        # multiple indices to be stored
        self._indices = {}

        # initialise a dictionary mapping nodes to documents
        #
        # this is used to provide an overall list of all nodes, and to
        # qualify links with document names, when the link to nodes in
        # other documents
        #
        # we add all the subindex names to the 'common nodes' list to
        # avoid warnings if any appear in multiple documents; the index
        # named with '@index' in each document will be added as the
        # files are read later
        self._node_docs = GuideNodeDocs()
        for subindex_name in subindex_names:
            self._node_docs.addcommonnode(subindex_name)

        # also store the list of subindex node names from the supplied
        # argument as we need it when we read the documents
        self._subindex_names = subindex_names

        # initialise the list of warnings at the set level to empty
        self._warnings = []

        # read in the document files in the set
        self.readfiles(filenames)


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


    def readfiles(self, filenames):
        """Read the list of document files into a set.
        """

        # go through the supplied list of filenames
        for filename in filenames:
            # read in that file and make a document
            doc = GuideDoc(filename, subindex_names=self._subindex_names)

            # add this document to the list of documents in the set
            self._docs.append(doc)

            # add the index node to the set of 'always local' nodes
            index_node_name = doc.getcmd(DOC_CMD_INDEX)
            if index_node_name:
                self._node_docs.addcommonnode(index_node_name)

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
                    doc.addwarning(f"over maximum size: {DOC_MAXSIZE} bytes")


    def print(self, *, readable=False):
        """Print out the set of guide documents to standard output, with
        a separator between each one.

        The 'readable' option controls whether a plain text version is
        rendered, rather than one including markup.  This will also skip
        any index nodes in each document, as they generally aren't very
        useful, in this format.

        'readable' not being set is primarily useful for debugging
        purposes only.
        """

        for doc in self._docs:
            # we only print the filename of this document is rendering
            # a non-readable 'debugging' format
            if not readable:
                print()
                print(f"=== {doc.getname()} ===")
                print()

            # print the formatted lines
            for line in doc.format(node_docs=self._node_docs,
                                   markup=not readable, skip_index=readable):
                print(line)


    def getnodedocs(self):
        """Return a dictionary keyed on the name of all nodes in the
        set, with the values as a list of the documents in which that
        node is defined.

        This is primarily useful as a debugging or informational
        function.
        """

        # create a dictionary of node names
        node_names = {}

        # go through the documents in the set, adding the names of all
        # the nodes to their entry in the above dictionary, creating it,
        # if required
        for doc in self._docs:
            for node_name in doc.getnodenames():
                node_names.setdefault(node_name, []).append(doc.getname())

        # return the dictionary
        return node_names


    def makeindices(self, *, line_maxlen=LINE_MAXLEN, indextermkey=_identity):
        """Make a consolidated indices for the set, merging together the
        index pages with the same node name as each other.

        This means that all index nodes which have the same name will
        be combined and have the same entries across the set.

        Keyword arguments:

        line_maxlen -- the maximum line length; lines longer than this
        will be word-wrapped (unless matching the 'literal' format).

        indextermkey -- a function which maps a term to its key to use
        use when sorting and grouping them in the index.
        """

        # initialise an empty set of indices as a dictionary
        #
        # the dictionary will be keyed off each index node name across
        # the set
        self._indices = {}

        # go through the documents in the set, building the consolidated
        # indices
        for doc in self._docs:
            # parse the indices in this document (which will consist of
            # the node named by the '@index' command, plus the
            # additional subindex nodes)
            doc.parseindices()

            # work through the indices in the document
            for index_name in doc.getindices():
                # add this index name to the common nodes set for the
                # consolidated index (so we don't create warnings about
                # the node existing in multiple documents, etc.)
                self._node_docs.addcommonnode(index_name)

                # if we haven't already started an index with the same
                # name as this one, create it
                if index_name not in self._indices:
                    self._indices[index_name] = (
                        GuideIndex(termkey=indextermkey))

                # merge this document's index into the consolidated one
                # under the same name
                self._indices[index_name].merge(doc.getindex(index_name))


        # create a dictionary, keyed off the index node name, of
        # formatted text indices from those built above
        formatted_indices = {
            index_name:
                self._indices[index_name].format(line_maxlen)
                    for index_name in self._indices }


        # go back through the documents in the set, replacing the indices
        for doc in self._docs:
            for index_name in doc.getindices():
                # get the existing index (for the header and footer lines)
                index = doc.getindex(index_name)

                # replace the node with the same name, using the header
                # and footer from the original node, and the new
                # consolidated index between
                doc.getnode(index_name).replacelines(
                    ((index.header + ['']) if index.header else [])
                    + formatted_indices[index_name]
                    + (([''] + index.footer) if index.footer else []))
