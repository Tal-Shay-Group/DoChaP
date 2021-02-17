#!/usr/bin/python
import subprocess
import sys
import os
import re
import pandas as pd

sys.path.append(os.getcwd())
from Director import SourceBuilder
from conf import all_species, SpConvert_EnsDomains, SpConvert_EnsShort


class OrthologsBuilder(SourceBuilder):
    """
    Dowload and parse Orthology tables
    """

    def __init__(self, all_species=all_species):
        """
        @type all_species: tuple
        """
        self.all_species = all_species
        self.speciesConvertor = SpConvert_EnsDomains
        self.speciesConvertorShort = SpConvert_EnsShort
        self.downloadPath = os.getcwd() + "/data/orthology/"
        self.dataTables = ()
        self.AllSpeciesDF = {}

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
        self.dataTables = self.dataTables + ("{}.{}.orthology.txt".format(species1, species2),)
        return commandPath

    def returnShellScripts(self, toFile=None):
        AllCommands = []
        for i in range(len(self.all_species)):
            for j in range(i, len(self.all_species)):
                if self.all_species[i] != self.all_species[j]:
                    AllCommands.append(self.createDownloadScripts(self.all_species[i], self.all_species[j]))
        if toFile is None:
            return self.shellScript
        else:
            with open(toFile, "a") as write:
                for shell in AllCommands:
                    write.write(shell + "\n")

    def downloader(self):
        output = dict()
        err = dict()
        scriptsCalc = int((len(self.all_species) ** 2 - len(self.all_species)) / 2)
        n = 0
        for i in range(len(self.all_species)):
            for j in range(i, len(self.all_species)):
                if self.all_species[i] != self.all_species[j]:
                    n += 1
                    shellCommand = self.createDownloadScripts(self.all_species[i], self.all_species[j])
                    subprocess.Popen(['chmod', 'u+x', shellCommand])
                    runScript = subprocess.Popen([shellCommand], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                 text=True)
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

    def parser(self):
        conv = {'gene_stable_ID': 'ID', 'gene_name': 'name', 'homology_type': 'type',
                'Human': 'H_sapiens', 'Rat': 'R_norvegicus', 'Mouse': 'M_musculus', 'Zebrafish': 'D_rerio',
                'Tropical_clawed_frog': 'X_tropicalis'}
        self.AllSpeciesDF = {}
        alltables = os.listdir(self.downloadPath)
        alltables = [table for table in alltables if table.endswith("orthology.txt")]
        for tab in alltables:
            s1 = tab.split(".")[0]
            s2 = tab.split(".")[1]
            # tablename = self.downloadPath + "{}.{}.orthology.txt".format(self.all_species[i], self.all_species[j])
            tablepath = self.downloadPath + tab
            df = pd.read_table(tablepath, sep='\t')
            df.columns = df.columns.str.replace(' ', '_')
            df.columns = df.columns.str.replace('Gene_stable', s1)
            df.columns = df.columns.str.replace('Gene', s1)
            for k, v in conv.items():
                df.columns = df.columns.str.replace(k, v)
            df = df.drop(s2 + "_type", axis=1)
            df = df[df.isna().sum(1) == 0]
            df[s1 + '_name'] = df[s1 + '_name'].str.upper()
            df[s2 + '_name'] = df[s2 + '_name'].str.upper()
            self.AllSpeciesDF[(s1, s2)] = df
        # for i in range(len(self.all_species)):
        #     for j in range(i, len(self.all_species)):
        # if self.all_species[i] != self.all_species[j]:
