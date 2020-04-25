# import ftplib
# import gzip
import os
import sys
# import datetime
import gffutils

# from Bio import SeqIO

sys.path.append(os.getcwd())
from recordTypes import *
from Director import SourceBuilder
from ftpDownload import ftpDownload


class EnsemblBuilder(SourceBuilder):
    """
    Download and Parse ensembl gff files
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
        self.SpeciesConvertor = {'M_musculus': 'mus_musculus', 'H_sapiens': 'homo_sapiens',
                                 'R_norvegicus': 'rattus_norvegicus', 'D_rerio': 'danio_rerio',
                                 'X_tropicalis': 'xenopus_tropicalis'}
        self.species = species
        self.savePath = os.getcwd() + '/data/{}/ensembl/'.format(self.species)
        self.gff = self.savePath + "genomic.gff3"
        self.Transcripts = {}
        self.Domains = {}
        self.Proteins = {}
        self.Genes = {}
        self.pro2trans = {}
        self.trans2pro = {}

    def downloader(self):
        skey = self.SpeciesConvertor[self.species]
        ftp_address = 'ftp.ensembl.org'
        ftp_path = '/pub/current_gff3/{}/'.format(skey)

        def FindFile(listOfFiles):
            for file in listOfFiles:
                if file[-7:] == "gff3.gz" and ".chr" not in file and "abinitio" not in file:
                    out = [[file[:-3], "genomic.gff3"]]
                    return out

        self.gff = self.savePath + "genomic.gff3"
        down = ftpDownload(species=skey, ftp_adress=ftp_address, ftp_path=ftp_path, savePath=self.savePath,
                           specifyPathFunc=FindFile)
        down.Download()

    def parser(self):
        fn = gffutils.example_filename(self.gff)
        db = gffutils.create_db(fn, ":memory:", merge_strategy="create_unique")
        # gffutils.create_db(fn, "DB.Ensembl.db", merge_strategy="create_unique")
        # db = gffutils.FeatureDB("DB.Ensembl.db")
        print("Collecting Transcripts data from gff file...")
        self.Transcripts = {}
        for t in db.features_of_type("mRNA"):
            newT = Transcript()
            newT.chrom = t.chrom
            newT.tx = (t.start - 1, t.end,)
            newT.strand = t.strand
            newT.ensembl = t["transcript_id"][0] + "." + t["version"][0]
            newT.gene_ensembl = t["Parent"][0].split(":")[1]
            newT.geneSymb = t["Name"][0].split("-")[0]
            self.Transcripts[newT.ensembl] = newT
        print("Collecting CDS data from gff file...")
        for cds in db.features_of_type("CDS"):
            par = [info if info.startswith("transcript:") else ":0" for info in cds["Parent"]][0]
            ref = par.split(":")[1] + "." + db[par]["version"][0]
            if ref[0] == '0' or ref not in self.Transcripts.keys():
                continue
            current_CDS = self.Transcripts[ref].CDS
            if current_CDS is not None:
                cds_start = cds.start if cds.start < current_CDS[0] else current_CDS[0]
                cds_end = cds.end if cds.end > current_CDS[1] else current_CDS[1]
            else:
                self.Transcripts[ref].protein_ensembl = cds["protein_id"][0]
                cds_start = cds.start - 1  # gff format is 1 based start, the manipulations are for 0 based start
                cds_end = cds.end
            self.Transcripts[ref].CDS = (cds_start, cds_end,)
        print("Collecting Exons data from gff file...")
        for e in db.features_of_type("exon"):
            par = [info if info.startswith("transcript:") else ":0" for info in e["Parent"]][0]
            ref = par.split(":")[1] + "." + db[par]["version"][0]
            if ref not in self.Transcripts.keys():
                continue
            orderInT = int(e["rank"][0])
            l_orig = len(self.Transcripts[ref].exon_starts)
            self.Transcripts[ref].exon_starts = self.Transcripts[ref].exon_starts + [None] * (orderInT - l_orig)
            self.Transcripts[ref].exon_ends = self.Transcripts[ref].exon_ends + [None] * (orderInT - l_orig)
            self.Transcripts[ref].exon_starts[orderInT - 1] = e.start - 1
            self.Transcripts[ref].exon_ends[orderInT - 1] = e.end
        for t in self.Transcripts.values():
            if t.strand == "-":
                t.exon_starts = t.exon_starts[::-1]
                t.exon_ends = t.exon_ends[::-1]
