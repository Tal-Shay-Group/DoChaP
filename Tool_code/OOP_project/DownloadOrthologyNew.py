#!/usr/bin/python
import subprocess
import sys
import os
import re
import pandas as pd

sys.path.append(os.getcwd())
from Director import SourceBuilder


class OrthologsBuilder(SourceBuilder):
    """
    Dowload and parse Orthology tables
    """

    def __init__(self, species=('M_musculus', 'H_sapiens', 'R_norvegicus', 'D_rerio', 'X_tropicalis'), download=False):
        """
        @type species: tuple
        """
        self.species = species
        self.speciesConvertor = {'M_musculus': 'mmusculus', 'H_sapiens': 'hsapiens',
                                 'R_norvegicus': 'rnorvegicus', 'D_rerio': 'drerio',
                                 'X_tropicalis': 'xtropicalis'}
        self.speciesConvertorShort = {'M_musculus': 'MUSG', 'H_sapiens': 'G', 'R_norvegicus': 'RNOG',
                                      'D_rerio': 'DARG', 'X_tropicalis': 'XETG'}
        self.downloadPath = os.getcwd() + "/data/orthology/"
        if not download:
            self.scriptsList = [self.downloadPath + "/" + file for file in os.listdir(self.downloadPath) if file[-13:] == "orthology.txt"]
        self.scriptsList = ()
        self.OrthoTable = None

    def createDownloadScripts(self, species1, species2):
        os.makedirs(self.downloadPath, exist_ok=True)
        replaceDict = {"output.txt": self.downloadPath + "{}.{}.orthology.txt".format(species1, species2),
                       "MainSpecies": self.speciesConvertor[species1] + "_gene_ensembl",
                       "Comp1": self.speciesConvertor[species2]}
        commandPath = os.getcwd() + "/BioMart.Orthologs.Couples.{}.{}.sh".format(species1, species2)
        with open(os.getcwd() + "/BioMart.Orthologs.Couples.Template.sh", "r") as template:
            with open(commandPath, "w") as writo:
                for line in template:
                    for key in replaceDict:
                        if key in line:
                            line = line.replace(key, replaceDict[key])
                    writo.write(line)
        return commandPath

    def downloader(self):
        output = dict()
        err = dict()
        scriptsCalc = int((len(self.species)**2 - len(self.species))/2)
        n = 0
        for i in range(len(self.species)):
            for j in range(i, len(self.species)):
                if self.species[i] != self.species[j]:
                    n += 1
                    shellCommand = self.createDownloadScripts(self.species[i], self.species[j])
                    runScript = subprocess.Popen([shellCommand], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    output[shellCommand], err[shellCommand] = runScript.communicate()
                    print("poll(): " + str(runScript.poll()))
                    if n == scriptsCalc:
                        check = None
                        while check is None:
                            print("waiting for last job to finish")
                            check = runScript.wait()
                        print("last job has finished")
        print("Validating successful downloads...")
        for key in err.keys():
            if err[key] is not '':
                print(key)
                print(err[key])
            else:
                print("script: " + key + " has finished running without errors")



ortho = OrthologsBuilder(download=True)
ortho.downloader()


