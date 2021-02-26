#!/usr/bin/python
import sys
import os
import time

sys.path.append(os.getcwd())
from Director import Director
from OrthologsBuilder import *
from SpeciesDB import *


def timer(start,end):
    hours, rem = divmod(end-start, 3600)
    minutes, seconds = divmod(rem, 60)
    return "{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds)


if __name__ == "__main__":
    start_time = time.time()
    download = False
    withEns = True
    sp = 'M_musculus'

    print("Running DBbuilder with Download {} and withENS {}".format(download, withEns))
    print("===========Current Species: {}===========".format(sp))
    bp = time.time()
    dbBuild = dbBuilder(sp, download=download, withEns=withEns)
    print("#### Species data collect & merge duration: " + timer(bp, time.time()))
    # dbBuild.create_tables_db(merged=False)
    # bp = time.time()
    # dbBuild.fill_in_db(CollectDomainsFromMerged=False, merged=False)
    # print("Filling {} completed!".format(dbBuild.dbName))
    # print("#### Duration: " + timer(bp, time.time()))
    # print("#### Full run duration: " + timer(start_time, time.time()))
