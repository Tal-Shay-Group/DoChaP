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
    species = ['H_sapiens', 'M_musculus', 'R_norvegicus', 'D_rerio', 'X_tropicalis']

    print("Running DBbuilder with Download {} and withENS {}".format(download, withEns))

    bp = time.time()
    director = Director()
    orthologs = OrthologsBuilder(species=species)
    director.setBuilder(orthologs)
    director.collectFromSource(download=True)
    print("#### Orthologs collection duration: " + timer(bp, time.time()))

    spl = len(species)
    spnum = 1
    for sp in species:
        print("===========Current Species: {}===========".format(sp))
        bp = time.time()
        dbBuild = dbBuilder(sp, download=download, withEns=withEns)
        print("****")
        print("#### Species data collect & merge duration: " + timer(bp, time.time()))
        if spnum == 1:
            dbBuild.create_tables_db(merged=True)
        bp = time.time()
        dbBuild.fill_in_db(merged=True)
        print("Adding species {} to DB {} completed!".format(sp, dbBuild.dbName))
        print("#### Duration: " + timer(bp, time.time()))
        if spnum == spl:
            dbBuild.create_index()
            dbBuild.AddOrthology(orthologs.AllSpeciesDF)
        if sp in ['M_musculus', 'H_sapiens']:
            dbBuild.create_tables_db(merged=False)
            bp = time.time()
            dbBuild.fill_in_db(merged=False)
            print("Filling {} completed!".format(dbBuild.dbName))
            print("#### Duration: " + timer(bp, time.time()))
        spnum += 1
    print("#### Full run duration: " + timer(start_time, time.time()))
