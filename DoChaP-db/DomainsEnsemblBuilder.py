import subprocess
import sys
import os
import pandas as pd
import re

sys.path.append(os.getcwd())
from Director import SourceBuilder
from recordTypes import *
from conf import SpConvert_EnsDomains, external


# BioMart serves these attributes under two header layouts. Newer marts return
# the accession and its version pre-joined in a single "<X> stable ID version"
# column; older ones return them split across "<X> stable ID" and
# "Version (<x>)". Both are valid downloads - only the layout differs - so the
# split form is joined back together and the rest of the pipeline sees one shape.
DOMAIN_ID_COLUMNS = (
    ("Transcript stable ID version", "Transcript stable ID", "Version (transcript)"),
    ("Protein stable ID version", "Protein stable ID", "Version (protein)"),
)


def isDomainsHeader(line):
    """True if `line` is a BioMart domains-table header, in either layout."""
    first = line.lstrip()
    if first[:1] == '<':  # HTML error/redirect page
        return False
    return first.startswith("Transcript stable ID")


def normalizeDomainColumns(df, path=""):
    """Ensure the joined '<X> stable ID version' columns exist on `df`.

    Tables in the split layout are joined here; tables already in the joined
    layout pass through untouched. Rows whose accession or version is missing
    get NaN, so the caller's dropna() discards them as before.
    """
    for joined, accession, version in DOMAIN_ID_COLUMNS:
        if joined in df.columns:
            continue
        if accession not in df.columns or version not in df.columns:
            raise RuntimeError(
                "{} is not a valid BioMart domains table (columns: {}). Expected "
                "either a '{}' column or the '{}' + '{}' pair. A table with neither "
                "is most likely an Ensembl error page saved during a download "
                "outage - delete it and re-download.".format(
                    path, list(df.columns), joined, accession, version))
        acc = df[accession]
        ver = pd.to_numeric(df[version], errors="coerce")
        usable = acc.notna() & ver.notna()
        df[joined] = None
        df.loc[usable, joined] = acc[usable].astype(str) + "." + \
            ver[usable].astype(int).astype(str)
        df = df.drop(columns=[accession, version])
    return df


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
        """A valid BioMart domains TSV starts with a 'Transcript stable ID'
        header (either layout, see isDomainsHeader), not an HTML error/status
        page (e.g. Ensembl's 'Service unavailable' returned with HTTP 200,
        which wget saves as-is). Files failing this check get deleted and
        re-downloaded, so it must not reject a merely older layout."""
        try:
            with open(path, 'r') as f:
                first = f.readline()
        except OSError:
            return False
        return isDomainsHeader(first)

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
