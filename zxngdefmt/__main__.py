#!/usr/bin/env python3



import argparse
import sys

from . import __version__, GuideSet, indextermkey_factory



# --- parse arguments ---



parser = argparse.ArgumentParser(
    # override the program name as running this as a __main__ inside a
    # module directory will use '__main__' by default - this name isn't
    # necessarily correct, but it looks better than that
    prog="zxngdefmt",

    # we want the epilog help output to be printed as it and not
    # reformatted or line wrapped
    formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument(
    "-o", "--output-dir",
    help="directory to write out formatted NextGuide files")

parser.add_argument(
    "-i", "--index",
    action="store_true",
    help="recreate index pages, including common index across set")

parser.add_argument(
    "-I", "--subindex",
    default=[],
    action="append",
    help="additional node name to process as a subindex, besides the"
         " one named in the '@index' document command")

parser.add_argument(
    "-p", "--index-term-prefix",
    metavar="PREFIX",
    default=[],
    action="append",
    help="leading strings to ignore when sorting and grouping index"
         " terms - e.g. if set to '.' then '.term' as a term will be"
         " sorted and grouped under 't'; note this can be a string and"
         " not just a single character, and this option can be used"
         " multiple times for multiple prefixes")

parser.add_argument(
    "-w", "--no-warnings",
    action="store_true",
    help="suppress printing of warnings encountered during formatting"
         " to stdandard error")

parser.add_argument(
    "-n", "--nodes",
    action="store_true",
    help="print a list of all nodes in the set to standard output")

parser.add_argument(
    "-r", "--readable",
    action="store_true",
    default=False,
    help="render a readable, plain text version of the guide set to"
         " standard output: remove markup, skip index pages, highlight"
         " links, don't print filenames; only used if -o is not"
         " specified")

parser.add_argument(
    "-v", "--version",
    action="version",
    version=__version__)

parser.add_argument(
    "file",
    nargs='+',
    help="filename of NextGuide document(s) to read")


args = parser.parse_args()



# --- process arguments ---



# read in the specified list of NextGuide files
guide_set = GuideSet(args.file, subindex_names=args.subindex)

# use a factory function to make a function which will return the key
# for index term sorting and grouping
indextermkey_fn = indextermkey_factory(args.index_term_prefix)

# parse, recreate and replace the indices with formatted, set-wide ones
if args.index:
    guide_set.makeindices(indextermkey=indextermkey_fn)

# if we're writing out formatted guide files, do that, otherwise just
# print the results to stdout (in readable format, if requested)
if args.output_dir:
    guide_set.writefiles(args.output_dir)
else:
    guide_set.print(readable=args.readable)

# if the 'list nodes' option is used, print the names of all nodes,
# alongside the document(s) in which they are defined
if args.nodes:
    node_docs = guide_set.getnodedocs()
    for node_name in sorted(node_docs):
        print(f"{node_name:20}", ", ".join(sorted(node_docs[node_name])))

# if warnings haven't been disabled, print those to stderr
if not args.no_warnings:
    warnings = guide_set.getwarnings()
    for warning in warnings:
        print(warning, file=sys.stderr)
