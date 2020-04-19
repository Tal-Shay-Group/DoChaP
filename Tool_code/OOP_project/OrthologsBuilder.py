import subprocess
import sys
import os
import pandas as pd
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

    def parser(self):
        spdL = []
        for spec in self.species:
            spd = pd.read_table(os.getcwd() + "/data/orthology/" + spec + ".orthology.txt", sep='\t',
                                names=[spec + "_ID", "O1_ID", "O1_name", "O1_type",
                                       "O2_ID", "O2_name", "O2_type",
                                       "O3_ID", "O3_name", "O3_type",
                                       "O4_ID", "O4_name", "O4_type",
                                       spec + "_name"])
            for col in ["O1", "O2", "O3", "O4"]:
                for record in spd[col + "_ID"]:
                    if type(record) is float:
                        continue
                    else:
                        for otherSpecies in self.species:
                            otherShort = self.speciesConvertorShort[otherSpecies]
                            if re.match(rf'ENS{otherShort}[0-9]', record):
                                changeCol = {col + "_ID": otherSpecies + "_ID", col + "_name": otherSpecies + "_name",
                                             col + "_type": otherSpecies + "_type"}
                                spd = spd.rename(columns=changeCol, errors="raise")
                                break
                        break
            spdL.append(spd)
        new = pd.concat(spdL, ignore_index=True)
        subset = new[['H_sapiens_ID', 'H_sapiens_name', 'M_musculus_ID', 'M_musculus_name',
                      'R_norvegicus_ID', 'R_norvegicus_name', 'D_rerio_ID', 'D_rerio_name',
                      'X_tropicalis_ID', 'X_tropicalis_name']].copy()
        subset = subset.drop_duplicates(ignore_index=True)
        #return subset
        for column in map(lambda x: x + '_ID', self.species):
            restColumns = list(subset.columns)
            restColumns.remove(column)
            subset = subset.groupby([column], as_index=False)[restColumns].agg(lambda x: '; '.join(set(map(str, x))))
        subset = subset.replace({'; nan': '', 'nan; ': ''}, regex=True)
        subset = subset.replace({'nan': None})
        self.OrthoTable = subset
