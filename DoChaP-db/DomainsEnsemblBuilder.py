import subprocess
import sys
import os
import pandas as pd
import re

sys.path.append(os.getcwd())
from Director import SourceBuilder
from recordTypes import *
from conf import SpConvert_EnsDomains, external


class DomainsEnsemblBuilder(SourceBuilder):
    """
    Download and parse Domains tables
    """

    def __init__(self, species):
        """
        @type species: tuple
        """
        self.species = species
        self.speciesConvertor = SpConvert_EnsDomains
        self.ExternalDomains = tuple(external)
        self.downloadPath = os.getcwd() + '/data/{}/ensembl/BioMart/'.format(self.species)
        self.shellScript = os.getcwd() + \
                           "/BioMart.ensembl.domains.{}.AllSources.sh".format(self.species)

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
        """This function calls the createDownloadScripts and then tryes to Run it.
        Currently this is not the best way of doing that, therefor the create download scripts is called from
        the module CreatAllDownloadScripts and then RunAllDownloads.bash is running the scripts in parallel.
        """
        self.createDownloadScripts()
        subprocess.Popen(['chmod', 'u+x', self.shellScript])
        runScript = subprocess.Popen([self.shellScript], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, err = runScript.communicate()
        print("poll(): " + str(runScript.poll()))
        check = None
        e = str(err)
        while check is None:
            print("waiting for job to finish")
            e = str(err)
            check = runScript.wait()
        print("Job has finished")
        print("Validating successful downloads...")
        if e == '':
            print(e)
        else:
            print("script has finished running without errors")
        # os.remove(self.shellScript)

    # def Parser(self):
    #     for extDB in self.ExternalDomains:
    #         df = pd.read_table(self.downloadPath + self.species + ".Domains.{}.txt".format(extDB),
    #                            sep="\t", header=0)
    #         df.columns = df.columns.str.replace(" ", "_")
    #         df.columns = df.columns.str.lower().str.replace(extDB+"_", "")
    #         df = df.dropna()
    #         conv = {"pf":"pfam", "sm":"smart"}
    #         for i, row in df.iterrows():
    #             id = row.id.lower()
    #             idtype = re.sub(r'\d+', '', id)
    #             if idtype in conv.keys():
    #                 id = id.replace(idtype, conv[idtype])
    #             if extDB == "interpro":
    #                 self.Domains[row.protein_stable_id_version] = self.Domains.get(row.protein_stable_id_version, []) + \
    #                                                               [Domain(ext_id=id, start=int(row.start),
    #                                                                       end=int(row.end), name=row.short_description,
    #                                                                       note=row.description)]
    #             else:
    #                 self.Domains[row.protein_stable_id_version] = self.Domains.get(row.protein_stable_id_version, []) + \
    #                                                           [Domain(ext_id=id, start=int(row.start), end=int(row.end))]
    #             self.pro2trans[row.protein_stable_id_version] = row.transcript_stable_id_version
    #             self.trans2pro[row.transcript_stable_id_version] = row.protein_stable_id_version
