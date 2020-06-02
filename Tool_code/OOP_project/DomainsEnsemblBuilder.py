import subprocess
import sys
import os
import pandas as pd
import re

sys.path.append(os.getcwd())
from Director import SourceBuilder
from recordTypes import *


class DomainsEnsemblBuilder(SourceBuilder):
    """
    Dowload and parse Domains tables
    """

    def __init__(self,species):
        """
        @type species: tuple
        """
        self.species = species
        self.speciesConvertor = {'M_musculus': 'mmusculus', 'H_sapiens': 'hsapiens',
                                 'R_norvegicus': 'rnorvegicus', 'D_rerio': 'drerio',
                                 'X_tropicalis': 'xtropicalis'}
        self.ExtSources = ("pfam", "smart", "cdd", "tigrfam", "interpro")
        self.downloadPath = os.getcwd() + '/data/{}/ensembl/BioMart/'.format(self.species)
        self.shellScript = os.getcwd() + \
                           "/BioMart.ensembl.domains.{}.AllSources.sh".format(self.species)
        # self.Domains = {}
        # self.Proteins = {}
        # self.pro2trans = {}
        # self.trans2pro = {}

    def createDownloadScripts(self):
        scriptList = tuple()
        os.makedirs(self.downloadPath, exist_ok=True)
        replaceDict = {"Pathspecies": self.downloadPath + self.species,
                        "EnsSpecies": self.speciesConvertor[self.species]}
        with open(os.getcwd() + "/BioMart.ensembl.domains.template.sh", "r") as template:
            with open(self.shellScript, "w") as writo:
                for line in template:
                    for key in replaceDict:
                        if key in line:
                            line = line.replace(key, replaceDict[key])
                    writo.write(line)

    def returnShellScripts(self, toFile=None):
        self.createDownloadScripts()
        if toFile is None:
            return self.shellScript
        else:
            with open(toFile, "a") as write:
                write.write(self.shellScript + "\n")

    def downloader(self):
        self.createDownloadScripts()
        runScript = subprocess.Popen([self.shellScript], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, err = runScript.communicate()
        print("poll(): " + str(runScript.poll()))
        check = None
        while check is None:
            print("waiting for job to finish")
            check = runScript.wait()
        print("Job has finished")
        print("Validating successful downloads...")
        if err is not '':
            print(err)
        else:
            print("script has finished running without errors")
        # os.remove(self.shellScript)

    def Parser(self):
        for extDB in self.ExtSources:
            df = pd.read_table(self.downloadPath + self.species + ".Domains.{}.txt".format(extDB),
                               sep="\t", header=0)
            df.columns = df.columns.str.replace(" ", "_")
            df.columns = df.columns.str.lower().str.replace(extDB+"_", "")
            df = df.dropna()
            conv = {"pf":"pfam", "sm":"smart"}
            for i, row in df.iterrows():
                id = row.id.lower()
                idtype= re.sub(r'\d+', '', id)
                if idtype in conv.keys():
                    id = id.replace(idtype, conv[idtype])
                break
                if extDB == "interpro":
                    self.Domains[row.protein_stable_id_version] = self.Domains.get(row.protein_stable_id_version, []) + \
                                                                  [Domain(ext_id=id, start=int(row.start),
                                                                          end=int(row.end), name=row.short_description,
                                                                          note=row.description)]
                else:
                    self.Domains[row.protein_stable_id_version] = self.Domains.get(row.protein_stable_id_version, []) + \
                                                              [Domain(ext_id=id, start=int(row.start), end=int(row.end))]
                self.pro2trans[row.protein_stable_id_version] = row.transcript_stable_id_version
                self.trans2pro[row.transcript_stable_id_version] = row.protein_stable_id_version
