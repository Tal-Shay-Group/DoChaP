import subprocess
import sys
import os
import pandas as pd
import re

sys.path.append(os.getcwd())
from Director import SourceBuilder


class DomainsEnsemblBuilder(SourceBuilder):
    """
    Dowload and parse Domains tables
    """

    def __init__(self,species, download=False):
        """
        @type species: tuple
        """
        self.species = species
        self.speciesConvertor = {'M_musculus': 'mmusculus', 'H_sapiens': 'hsapiens',
                                 'R_norvegicus': 'rnorvegicus', 'D_rerio': 'drerio',
                                 'X_tropicalis': 'xtropicalis'}
        self.ExtSources = ("pfam", "smart", "cdd", "tigrfam")
        self.downloadPath = os.getcwd() + '/data/{}/ensembl/BioMart/'.format(self.species)
        #if not download:
        #    self.scriptsList = [self.downloadPath + "/" + file for file in os.listdir(self.downloadPath) if file[-13:] == "orthology.txt"]
        self.scriptsList = ()
        self.OrthoTable = None

    def createDownloadScripts(self):
        scriptList = tuple()
        os.makedirs(self.downloadPath, exist_ok=True)
        for extDB in self.ExtSources:
            replaceDict = {"output.txt": self.downloadPath + "{}.Domains.{}.txt".format(self.species, extDB),
                            "MainSpecies": self.speciesConvertor[self.species],
                           "extDB": extDB}
            with open(os.getcwd() + "/BioMart.ensembl.domains.template.sh", "r") as template:
                with open(os.getcwd() +
                          "/BioMart.ensembl.domains.{}.{}.sh".format(self.species, extDB), "w") as writo:
                    for line in template:
                        for key in replaceDict:
                            if key in line:
                                line = line.replace(key, replaceDict[key])
                        writo.write(line)
                    scriptList = scriptList + (os.getcwd() + "/BioMart.ensembl.domains.{}.{}.sh".format(self.species, extDB),)
        self.scriptsList = scriptList

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
        for script in self.scriptsList:
            os.remove(script)

