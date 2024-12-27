#!/usr/bin/env python3



import os
import sys

from . import GuideSet


os.chdir("../tbblue/docs/guides")

guide_set = GuideSet(["NextBASIC.gde", "NextBASIC_pt2.gde"])

guide_set.print()

w = guide_set.getwarnings()
if w:
    print("Warnings:", file=sys.stderr)
    for w1 in w:
        print('-', w1, file=sys.stderr)

guide_set.parseindex()

print("INDEX:", file=sys.stderr)
print(guide_set.index, file=sys.stderr)