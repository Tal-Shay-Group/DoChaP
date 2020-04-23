#!/usr/bin/python
import sys
import os

sys.path.append(os.getcwd())
from Director import Director
from OrthologsBuilder import *
from SpeciesDB import *

if __name__ == "__main__":
    download = False
    withEns = False
    species = ['M_musculus', 'H_sapiens', 'R_norvegicus', 'D_rerio', 'X_tropicalis']

    print("Running DBbuilder with Download {} and withENS {}".format(download, withEns))

    director = Director()
    orthologs = OrthologsBuilder(species=species)
    director.setBuilder(orthologs)
    director.collectFromSource(download=download)

    spl = len(species)
    spnum = 1
    for sp in species:
        print("===========Current Species: {}===========".format(sp))
        dbBuild = dbBuilder(sp, download=download, withEns=withEns)
        if spnum == 1:
            dbBuild.create_tables_db(merged=True)
        dbBuild.fill_in_db(merged=True)
        print("Adding species {} to DB {} completed!".format(sp, dbBuild.dbName))
        if spnum == spl:
            dbBuild.create_index()
            dbBuild.AddOrthology(orthologs.AllSpeciesDF)

        dbBuild.create_tables_db(merged=False)
        dbBuild.fill_in_db(merged=False)
        spnum += 1
        print("Filling {} completed!".format(dbBuild.dbName))
