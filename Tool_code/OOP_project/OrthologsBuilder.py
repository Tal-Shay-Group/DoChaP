import subprocess
from Tool_code.OOP_project.Director import SourceBuilder


class OrthologsBuilder(SourceBuilder):
    """
    Dowload and parse Orthology tables
    """

    def __init__(self, species = {'M_musculus', 'H_sapiens', 'R_norvegicus', 'D_rerio', 'X_tropicalis'}):
        super().__init__(species)
        self.species = species
        self.speciesConvertor = {'M_musculus': 'mmusculus', 'H_sapiens': 'hsapiens',
                                 'R_norvegicus': 'rnorvegicus', 'D_rerio': 'drerio',
                                 'X_tropicalis': 'xtropicalis'}
        self.fileList = None

    def setSpecies(self, speciesTuple):
        """adds species to the species tuple"""
        self.species = self.species + speciesTuple

    def setFileList(self, fileList):
        self.fileList = fileList

    def createDownloadScripts(self):
        scriptList = tuple()
        for species in self.species:
            replaceDict = {"output.txt": "{}.orthology.txt".format(species),
                           "MainSpecies": self.speciesConvertor[species]}
            addcomps = 1
            for compSpec in self.species:
                if compSpec is not species:
                    replaceDict["Comp" + str(addcomps)] = self.speciesConvertor[compSpec]
                    addcomps += 1
            with open("BioMart.orthologs.template.sh", "r") as template:
                with open("BioMart.orthologs.{}.sh".format(species), "w") as writo:
                    for line in template:
                        for key in replaceDict:
                            if key in line:
                                line = line.replace(key, replaceDict[key])
                        writo.write(line)
                    scriptList = scriptList + ("BioMart.orthologs.{}.sh".format(species),)
        self.setFileList(scriptList)

    def downloader(self):
        output = dict()
        err = dict()
        iterlen = len(self.fileList)
        n = 0
        for shellCommand in self.fileList:
            n += 1
            runScript = subprocess.Popen([shellCommand], stdout=subprocess.PIPE, stder=subprocess.PIPE, text=True)
            output[shellCommand], err[shellCommand] = runScript.communicate()
            if runScript.poll() is not None or 0:
                raise ValueError("Error in the run of " + shellCommand + "; stderr: " + err[shellCommand])
            if n == iterlen:
                check = None
                while check is None:
                    print("waiting for last job to finish")
                    check = runScript.wait()
                print("last job has finished")
        print("Validating successful downloads...")
        for key in err.keys():
            if err[key] is not '':
                raise ValueError("Error in the run of " + key + "; stderr: " + err[key])
            else:
                print("script: " + key + " has finished running without errors")