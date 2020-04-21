#!/usr/bin/python
import subprocess
import sys
import os
import re

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

    def setSpecies(self, speciesTuple):
        """adds species to the species tuple"""
        self.species = self.species + speciesTuple

    def setScriptsList(self, scriptsList):
        self.scriptsList = scriptsList

    def createDownloadScripts(self):
        scriptList = tuple()
        os.makedirs(self.downloadPath, exist_ok=True)
        for species in self.species:
            replaceDict = {"output.txt": self.downloadPath + "{}.orthology.txt".format(species),
                           "MainSpecies": self.speciesConvertor[species] + "_gene_ensembl"}
            addcomps = 1
            for compSpec in self.species:
                if compSpec is not species:
                    replaceDict["Comp" + str(addcomps)] = self.speciesConvertor[compSpec]
                    addcomps += 1
            with open(os.getcwd() + "/BioMart.orthologs.template.sh", "r") as template:
                with open(os.getcwd() + "/BioMart.orthologs.{}.sh".format(species), "w") as writo:
                    for line in template:
                        for key in replaceDict:
                            if key in line:
                                line = line.replace(key, replaceDict[key])
                        writo.write(line)
                    scriptList = scriptList + (os.getcwd() + "/BioMart.orthologs.{}.sh".format(species),)
        self.setScriptsList(scriptList)

    def downloader(self):
        output = dict()
        err = dict()
        if self.scriptsList == ():
            self.createDownloadScripts()
        iterlen = len(self.scriptsList)
        n = 0
        for shellCommand in self.scriptsList:
            n += 1
            runScript = subprocess.Popen([shellCommand], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output[shellCommand], err[shellCommand] = runScript.communicate()
            print("poll(): " + str(runScript.poll()))
            # if runScript.poll() is not None or 0:
            # raise ValueError("Error in the run of " + shellCommand + "; stderr: " + err[shellCommand])
            if n == iterlen:
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
