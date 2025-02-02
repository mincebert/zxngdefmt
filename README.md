ZX Spectrum Next Guide Formatter
================================

The ZX Spectrum Next operating system comes with a hypertext viewer called
_NextGuide_ which is used for viewing online information, including system
documentation, similar to _AmigaGuide_ on the Commodore Amiga.

NextGuide requires that documents are preformatted with regards line length and
word wrap.  The hypertext links and formatting (justification, attributes,
etc.) are achieved through markup commands, which can make it difficult to
calculate when to wrap a line of text to fit on the screen correctly.

In addition, the documents need to contain commands linking pages together,
e.g. to the next and previous nodes (pages).  As nodes are inserted, moved or
removed, these must be adjusted manually.

Finally, links can point to nodes in other documents (in version 1.1 and
later).  If a document is part of a set, and nodes are moved between documents,
as the set is reorganised, it is difficult to maintain a link to the correct
document.

This utility, `zxngdefmt`, attempts to resolve these issues by processing the
source documents to perform a number of tasks:

* calculate displayed line lengths of word wrap text
* populate links between previous and next nodes in a document automatically
* fix links to nodes in other documents by qualifying them with the correct
  document name
* automatically consolidate index nodes across a set of documents into a single
  index
* check documents for broken links and other mistakes

These functions are described below.

Usage
-----

The utility is an excecutable Python module and can be run with the `-m`
option and the name of the module.  `-h` gives help:

```
usage: zxngdefmt [-h] [-o OUTPUT_DIR] [-i] [-I SUBINDEX] [-p PREFIX] [-w] [-n]
                 [-r] [-v]
                 file [file ...]

positional arguments:
  file                  filename of NextGuide document(s) to read

options:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        directory to write out formatted NextGuide files
  -i, --index           recreate index pages, including common index across
                        set
  -I SUBINDEX, --subindex SUBINDEX
                        additional node name to process as a subindex, besides
                        the one named in the '@index' document command
  -p PREFIX, --index-term-prefix PREFIX
                        leading strings to ignore when sorting and grouping
                        index terms - e.g. if set to '.' then '.term' as a
                        term will be sorted and grouped under 't'; note this
                        can be a string and not just a single character, and
                        this option can be used multiple times for multiple
                        prefixes
  -w, --no-warnings     suppress printing of warnings encountered during
                        formatting to stdandard error
  -n, --nodes           print a list of all nodes in the set to standard
                        output
  -r, --readable        render a readable, plain text version of the guide set
                        to standard output: remove markup, skip index pages,
                        highlight links, don't print filenames; only used if
                        -o is not specified
  -v, --version         show program's version number and exit
```

Word wrap
---------

The displayed length of lines, without markup commands, are calculated and
lines in the source document will be word wrapped at the appropriate length (80
characters).

There are some exceptions to this, with lines matching certain criteria being
treated as _literal_ lines that have been preformatted and shouldn't be
processed.  These are lines with:

* leading spaces,
* three or more consecutive spaces,
* lines with _header_ commands (`@{hN}`),
* lines with centred or right-justified text (`@{c}` or `@{r}`), or
* lines consisting solely of a single link (`@{"..." LINK ...}`).

These are set to avoid having to manually override the formatting performed by
the utility, in the vast majority of cases.

Adjacent node link completion
-----------------------------

If the `@prev` or `@next` command is not defined for a particular node, the
previous or next node in the document are automatically inserted, maintaining
the correct order for stepping through the nodes in a guide.

If the `@toc` (table of contents) command is not defined for a node, the value
from the previous node will be re-used.  This allows the contents node to be
specified once at the beginning, or only as it needs to change.

To avoid these being automatically completed (especially `@toc`), the value
"`-`" can be specified.

Fix links to other documents
----------------------------

The utility can process a set of documents in one go, allowing it to build up
a table of which node is in which document.  If a node contains a link to a
node which is in another document in the set, the target of that link will be
qualified with the document name, when it is written out.

For example, if _Node1_ in _Document1_ contains a link command of the form
`@{" to Node 2 " LINK Node2}`, and _Node2_ resides in _Document2_, the link
will be rewritten to `@{" to Node 2 " LINK Document2/Node2}`, which will instruct the NextGuide viewer to load the `Document2` guide file and select
`Node2`.

Consolidated index
------------------

NextGuide documents support a single _index_ page which can be visited by
pushing `i` (or selecting a link to it).  If a particular guide set is spread
across multiple documents, this can make maintaining a large index, including
all the terms and the links to the appropriate nodes, difficult.

If this function is enabled (through the `-i` option), the utility will find
the index node in each document (as identified by the `@index` command) and
parse the lines in it to create a single, consolidated index for the set.

For this to work, lines in the index node must match a very specific format:

* they can start with 0-2 spaces, followed by
* the _term_ - a piece of static text (with no more than two spaces between
  each word), or a `LINK` command, followed by
* 3 or more spaces, followed by
* the _references_ - a list of `LINK`s separated by one comma and zero or more
  spaces

If a line starts with 5 or more spaces, then contains a list of references, it
continues the term used on the previous line.

This information is used to assemble a single index containing all terms and,
for each term, all the references.  The terms in the index are sorted into
ASCIIbetical order, with all non alphanumeric characters first (i.e. symbols).

Additional node names can be specified as providing indexes using the `-I`
(subindex) option.  These will be consolidated and processed in the same way.

Note: there is a limitation of 255 links per node.  The program will produce a
warning if this is exceeded (on any node, including a generated index node)
but it is currently not worked around.  A solution may be to split the index
into two tiers, but this can be worked around manually using the subindex
feature.

Checking
--------

All the links made in a guide set, either through the `@{"..." LINK ...}`
command, or through node/document commands (such as `@next` and `@toc`), will
be checked to ensure that the document does not contain any broken links to
non-existent nodes.

If a node name is re-used within a document or across two documents in a set,
a warning will be generated.  This latter restriction is to avoid ambiguity
when fixing links across documents.  The index node is exempted from this
restriction.

For reference purposes, with the `-n` option, the utility can also output a
list of all nodes in the set, along with this document they appear in, sorted
by node name order.

Readable, plain-text version
----------------------------

The `-r` option will generate a "readable" version of the guide set in plain
text, without markup, and print it to standard output.

This is useful if a version of the guide that doesn't need the NextGuide
viewer (or a Spectrum Next) is required.
