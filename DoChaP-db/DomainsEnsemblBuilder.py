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

    @staticmethod
    def _isValidDomainFile(path):
        """A valid BioMart domains TSV starts with the 'Transcript stable ID
        version' header, not an HTML error/status page (e.g. Ensembl's
        'Service unavailable' returned with HTTP 200, which wget saves as-is)."""
        try:
            with open(path, 'r') as f:
                first = f.readline().lstrip()
        except OSError:
            return False
        if first[:1] == '<':  # HTML error/redirect page
            return False
        return first.startswith("Transcript stable ID version")

    def _expectedFiles(self):
        return [self.downloadPath + self.species + ".Domains.{}.txt".format(extDB)
                for extDB in self.ExternalDomains
                if not (self.species == 'R_norvegicus' and extDB == 'tigrfams')]

    def downloader(self, retries=5, backoff=15):
        """Runs the per-species BioMart download script, then verifies every
        expected domains file is real TSV (not an Ensembl error page). Bad
        files are deleted and the whole script retried, so a transient outage
        can't leave a corrupt file cached on disk for later parsing to trip on.
        """
        import time
        self.createDownloadScripts()
        subprocess.Popen(['chmod', 'u+x', self.shellScript]).wait()
        for attempt in range(1, retries + 1):
            print(f"\t running script (attempt {attempt}/{retries}): {self.shellScript}")
            runScript = subprocess.Popen([self.shellScript], stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True)
            output, err = runScript.communicate()
            print("poll(): " + str(runScript.poll()))
            bad = [p for p in self._expectedFiles() if not self._isValidDomainFile(p)]
            if not bad:
                print("Validating successful downloads... all domain tables are valid TSV.")
                # os.remove(self.shellScript)
                return
            for p in bad:
                print("\t invalid domain file (likely an Ensembl 'Service unavailable' "
                      "page): {}".format(os.path.basename(p)))
                if os.path.exists(p):
                    os.remove(p)  # never leave a bad file cached
            if attempt < retries:
                print("\t retrying in {}s...".format(backoff))
                time.sleep(backoff)
        raise RuntimeError(
            "Failed to download valid Ensembl domain tables for {} after {} attempts. "
            "BioMart returned an error page each time.".format(self.species, retries))

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
