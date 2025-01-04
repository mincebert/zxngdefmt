#!/usr/bin/env python3



import argparse
import os
import sys

from . import __version__, GuideSet



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
    "-w", "--no-warnings",
    action="store_true",
    help="suppress printing of warnings encountered during formatting"
         " to stderr")

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
guide_set = GuideSet(args.file)

# recreate and replace the indexes and make a common one for the set
if args.index:
    guide_set.makecommonindex()

# if we're writing out formatted guide files, do that, otherwise just
# print the results to stdout
if args.output_dir:
    guide_set.writefiles(args.output_dir)
else:
    guide_set.print()

# if warnings haven't been disabled, print those to stderr
if not args.no_warnings:
    warnings = guide_set.getwarnings()
    for warning in warnings:
        print(warning, file=sys.stderr)
