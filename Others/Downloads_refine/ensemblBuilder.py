from Bio import SeqIO
from recordTypes import *
import subprocess
from Director import SourceBuilder
import os
import pandas as pd
import re

class EnsemblBuilder(SourceBuilder):
    """
    Download and parse Ensembl domains tables
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
        self.speciesConvertor = {'M_musculus': 'mmusculus', 'H_sapiens': 'hsapiens',
                                 'R_norvegicus': 'rnorvegicus', 'D_rerio': 'drerio',
                                 'X_tropicalis': 'xtropicalis'}
        self.savePath = os.getcwd() + '/data/{}/ensembl/'.format(self.species)
        self.fileName = "{}.ensembl.domains.txt".format(self.species)
        self.scriptPath = None
        self.gene2pro = dict()
        self.pro2gene = dict()
        self.genes = dict()
        self.proteins = dict()
        self.domains = dict()
        self.ignoredDomains = dict()

    def setFileList(self, fileList):
        self.fileList = fileList

    def createDownloadScript(self):
        os.makedirs(self.savePath, exist_ok=True)
        scriptPath = os.getcwd() + "/BioMart.ensembl.domains.{}.sh".format(self.species)
        replaceDict = {"output.txt": self.savePath + self.fileName,
                       "MainSpecies": self.speciesConvertor[self.species]}
        with open(os.getcwd() + "/BioMart.ensembl.domains.template.sh", "r") as template:
            with open(scriptPath, "w") as writo:
                for line in template:
                    for key in replaceDict:
                        if key in line:
                            line = line.replace(key, replaceDict[key])
                    writo.write(line)
        self.scriptPath = scriptPath

    def downloader(self):
        runScript = subprocess.Popen([self.scriptPath], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, err = runScript.communicate()
        print("poll(): " + str(runScript.poll()))
        check = None
        while check is None:
            print("Downloading...")
            check = runScript.wait()
        print("Download has finished!")
        print("Validating successful downloads...")
        if err is not '':
            print(err)
        else:
            print("Download has finished without errors")

    def parser(self):
        data = pd.DataFrame(self.savePath + self.fileName)
        for file in self.fileList:
            for rec in SeqIO.parse(file, 'gb'):
                if rec.name in self.proteins.keys():
                    raise ('redundancy err ' + rec.name)
                if rec.name[0:2] == 'NP' or rec.name[0:2] == 'XP':  # takes both proteins and predictions!
                    protein, gene, transcript = self.protein_info(rec)
                    transcriptKey = transcript.split('.')[0]
                    regions = self.regions_from_record(rec)
                    self.domains[rec.name] = regions
                    self.proteins[rec.name] = protein
                    for ogene in self.genes:
                        if ogene.compareGenes(gene):
                            newgene = ogene.addTranscript(transcript)
                            self.genes[transcriptKey] = newgene
                        else:
                            self.genes[transcriptKey] = gene
                    self.pro2gene[rec.name] = transcript
                    self.gene2pro[transcriptKey] = rec.name


    def regions_from_record(self, record):
        '''
        This functions takes a record from a gpff file and parse it by finding all the features defined Regions
        and put them in a list of tuples where each tuple include the following information about the region:
            1- start position in the protein + 1 as all records are 0-based start!!!)
            2- end position in the protein (all records are 1-based stop!!!)
            3- name of the region
            4- note of the region - description
            5- id of the region based on the source (can start with pfam/smart/cl/cd etc...)
        The function returns a list of the regions in the record and a set of all the domains identified in this record.
        '''
        regions = [feature for feature in record.features if feature.type == 'Region']
        parsed = []
        # domains = set()
        for reg in regions:
            start = reg.location.start.position + 1  # all records are 0 based start!!!
            end = reg.location.end.position
            if len(
                    reg.qualifiers) > 1 and 'region_name' in reg.qualifiers and start != end:  # only looking at regions larger than 1
                name = reg.qualifiers['region_name'][0]
                if 'note' in reg.qualifiers:
                    note = reg.qualifiers['note'][0]
                else:
                    note = None
                if re.match(r"PRK\d+", name):
                    ext_id = name
                elif note is not None:
                    if 'propagated from UniProtKB' in note:
                        note = note
                        ext_id = None
                    elif ';' in note:
                        noteSplit = note.split('; ')
                        ext_id = noteSplit[-1]
                        note = note[:-len(ext_id)]
                    else:
                        ext_id = None
                else:
                    ext_id = None
                if 'db_xref' not in reg.qualifiers:
                    if ext_id is None:
                        # kicked.append(note)
                        continue
                    cdId = None
                    # domains = domains.union({ext_id})
                else:
                    xref = reg.qualifiers.get('db_xref', [])
                    cdId = [i.split(':')[-1] for i in xref if i.startswith('CDD')][0]
                    # domains = domains.union({cdId})
                try:
                    newDomain = Domain(ext_id=ext_id, start=start, end=end, cddId=cdId, name=name, note=note)
                    parsed.append(newDomain)
                except ValueError:
                    self.ignoredDomains.update({'extId': ext_id, 'CDD': cdId})
                    # print("ignoring Unsupported external IDs: " + str(ext_id) + '; '+ str(cdId))
                # parsed.append((start, end, name, note, ext_id, cdId))
        return parsed # domains, kicked

    def protein_info(self, record):
        '''
        This function takes s protein record of a gpff file and parse it to get all the protein information.
        it returns a tuple including the following information:
            1- refseq_id (not including the version)
            2- version of the sequence (full id will be refseq_id.version)
            3- product protein description
            4- length (number of aa)
        it also returns a string with the refseq_id of the gene
        '''
        withversion = record.id  # with version
        # refseq_id = record.name  # without version
        descr = record.description
        pro = [p for p in record.features if p.type == 'Protein'][0]
        length = pro.location.end.position  # length!!!
        try:
            note = pro.qualifiers['note'][0]
        except Exception:
            note = None
        cds = [c for c in record.features if c.type == 'CDS'][0]

        # gene_info = (cds.qualifiers.get('gene', [None])[0], cds.qualifiers.get('gene_synonym', [None])[0],
        #             cds.qualifiers.get('db_xref', []))
        transcript = cds.qualifiers['coded_by'][0].split(':')[0]
        xref = cds.qualifiers.get('db_xref', [])
        GeneID = [i.split(':')[-1] for i in xref if i.startswith('GeneID')][0]
        protein = Protein(refseq=withversion, ensembl=None, descr=descr, length=length, note=note)
        gene = Gene(GeneID=GeneID,
                    ensembl=None, symbol=cds.qualifiers.get('gene', [None])[0],
                    synonyms=cds.qualifiers.get('gene_synonym', [None])[0],
                    chromosome=None, strand=None, transcripts=None)
        return protein, gene, transcript

    def records(self):
        return self.parser()
