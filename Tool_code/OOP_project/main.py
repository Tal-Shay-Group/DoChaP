from OOP_project.Director import *
from OOP_project.OrthologsBuilder import *
from OOP_project.SpeciesDB import *

if __name__ == "__main__":

    species = ['M_musculus', 'H_sapiens', 'R_norvegicus', 'D_rerio', 'X_tropicalis']
    download = False

    director = Director()
    orthologs = OrthologsBuilder(species=['M_musculus', 'H_sapiens', 'R_norvegicus', 'D_rerio', 'X_tropicalis'])
    director.setBuilder(orthologs)
    director.collectFromSource(download=download)

    spl = len(species)
    spnum = 1
    for sp in species:
        dbBuild = dbBuilder(sp, download=False, merged=True, dbName=None)
        if spnum == 1:
            dbBuild.create_tables_db()
            spnum += 1
        dbBuild.fill_in_db()
        if spnum == spl:
            dbBuild.create_index()
            dbBuild.AddOrthology(orthologs.OrthoTable)
