import ftplib
import gzip
import os
import datetime
from Bio import SeqIO
import re
from OOP_project.recordTypes import *
from OOP_project.Director import SourceBuilder
import gffutils
from Bio import SeqIO


class RefseqBuilder(SourceBuilder):
    """
    Download and parse Genebank flatfiles
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
        self.SpeciesConvertor = {'M_musculus': 'Mus_musculus', 'H_sapiens': 'Homo_sapiens', 'R_norvegicus': 'rn6',
                                 'D_rerio': 'danRer11',
                                 'X_tropicalis': 'xenTro9'}
        self.species = species
        self.speciesTaxonomy = {"Mus_musculus": "vertebrate_mammalian", "Homo_sapiens": "vertebrate_mammalian"}
        self.savePath = os.getcwd() + '/data/{}/refseq/'.format(self.species)
        self.gff = self.savePath + "genomic.gff"
        self.gpff = self.savePath + "protein.gpff"
        self.Transcripts = {}
        self.Domains = {}
        self.Proteins = {}
        self.Genes = {}
        self.pro2trans = {}
        self.trans2pro = {}

    def downloader(self):
        username = 'anonymous'
        pswd = 'example@post.bgu.ac.il'
        skey = self.SpeciesConvertor[self.species]
        ftp_address = 'ftp.ncbi.nlm.nih.gov'
        print('connecting to: ' + ftp_address + '...')
        ftp = ftplib.FTP(ftp_address)
        print('logging in...')
        ftp.login(user=username, passwd=pswd)
        ftp_path = '/genomes/refseq/{}/{}/latest_assembly_versions/'.format(self.speciesTaxonomy[skey], skey)
        ftp.cwd(ftp_path.format(skey))
        print('looking for latest assembly version for - ' + self.species + '...')
        print('downloading files to : ' + self.savePath)
        filesInDir = ftp.nlst()
        if len(filesInDir) > 1:
            raise ValueError("More than 1 file in dir")
        else:
            genomeVersion = filesInDir[0]
        ftp.cwd(genomeVersion + "/")
        gff = [genomeVersion + "_genomic.gff", "genomic.gff"]
        gpff = [genomeVersion + "_protein.gpff", "protein.gpff"]
        for file in [gff, gpff]:
            filePath = self.savePath + file[1]
            os.makedirs(os.path.dirname(filePath), exist_ok=True)
            print('downloading: ', file[0], '...')
            ftp.sendcmd("TYPE i")
            # size = ftp.size(file[0])
            with open(filePath + '.gz', 'wb') as f:
                def callback(chunk):
                    f.write(chunk)

                ftp.retrbinary("RETR " + file[0] + '.gz', callback)
            print('extracting...')
            inp = gzip.GzipFile(filePath + '.gz', 'rb')
            s = inp.read()
            inp.close()
            with open(filePath, 'wb') as f_out:
                f_out.write(s)
            print('removing compressed file...')
            os.remove(filePath + '.gz')
        self.gff = self.savePath + gff[1]
        self.gpff = self.savePath + gpff[1]
        with open(os.path.dirname(self.savePath) + '/README.txt', 'w') as readme:
            print('Writing README description...')
            readme.write('# Updated on: ' + str(datetime.datetime.now().date()) + '\n\n')
            readme.write('# Files were downloaded from:\t' + ftp_address + ftp_path + '\n\n')
            readme.write('# List of downloaded files:\n')
            for file in [gff, gpff]:
                readme.write('\t' + file[0] + 'saved as :' + file[1] + '\n')
                readme.write('\n')
            readme.write('# Files were extracted succsessfully!')

    def parser(self):
        self.ParseGffRefseq()
        print("Collecting Proteins and Domains data from gpff file...")
        for rec in SeqIO.parse(self.gpff, 'gb'):
            if rec.name[0:2] == 'NP' or rec.name[0:2] == 'XP':  # takes both proteins and predictions!
                protein, gene, transcript = self.protein_info(rec)
                transcriptKey = transcript  # .split('.')[0]
                regions = self.regions_from_record(rec)
                self.Domains[protein.refseq] = regions
                self.Proteins[protein.refseq] = protein
                self.Genes[transcriptKey] = gene
                self.pro2trans[protein.refseq] = transcript
                self.trans2pro[transcriptKey] = protein.refseq

    def ParseGffRefseq(self):
        fn = gffutils.example_filename(self.gff)
        db = gffutils.create_db(fn, ":memory:", merge_strategy="warning")
        print("Collecting Transcripts data from gff file...")
        self.Transcripts = {}
        for t in db.features_of_type("mRNA"):
            newT = Transcript()
            newT.tx = (t.start, t.end,)
            newT.strand = t.strand
            newT.refseq = t["transcript_id"][0]
            newT.gene_GeneID = [info for info in t["Dbxref"] if info.startswith("GeneID")][0].split(":")[1]
            newT.geneSymb = t["gene"][0]
            self.Transcripts[newT.refseq] = newT
        print("Collecting CDS data from gff file...")
        for cds in db.features_of_type("CDS"):
            ref = [info if info.startswith("rna-") else '-0' for info in cds["Parent"]][0].split("-")[1]
            if ref[0] == '0':
                continue
            self.Transcripts[ref].protein_refseq = cds["Name"][0]
            self.Transcripts[ref].CDS = (cds.start, cds.end,)
        print("Collecting Exons data from gff file...")
        for e in db.features_of_type("exon"):
            if e["gbkey"][0] != "mRNA":
                continue
            ref = e["ID"][0].split("-")[1]
            orderInT = int(e["ID"][0].split("-")[2])
            l_orig = len(self.Transcripts[ref].exon_starts)
            self.Transcripts[ref].exon_starts = self.Transcripts[ref].exon_starts + [None] * (orderInT - l_orig)
            self.Transcripts[ref].exon_ends = self.Transcripts[ref].exon_ends + [None] * (orderInT - l_orig)
            self.Transcripts[ref].exon_starts[orderInT - 1] = e.start
            self.Transcripts[ref].exon_ends[orderInT - 1] = e.end

    def regions_from_record(self, record):
        """
        This functions takes a record from a gpff file and parse it by finding all the features defined Regions
        and put them in a list of tuples where each tuple include the following information about the region:
            1- start position in the protein + 1 as all records are 0-based start!!!)
            2- end position in the protein (all records are 1-based stop!!!)
            3- name of the region
            4- note of the region - description
            5- id of the region based on the source (can start with pfam/smart/cl/cd etc...)
        The function returns a list of the regions in the record and a set of all the domains identified in this record.
        """
        regions = [feature for feature in record.features if feature.type == 'Region']
        parsed = []
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
                        continue
                    cdId = None
                else:
                    xref = reg.qualifiers.get('db_xref', [])
                    cdId = [i.split(':')[-1] for i in xref if i.startswith('CDD')][0]
                try:
                    newDomain = Domain(ext_id=ext_id, start=start, end=end, cddId=cdId, name=name, note=note)
                    parsed.append(newDomain)
                except ValueError:
                    self.ignoredDomains.update({'extId': ext_id, 'CDD': cdId})
        return parsed

    def protein_info(self, record):
        """
        This function takes s protein record of a gpff file and parse it to get all the protein information.
        it returns a tuple including the following information:
            1- refseq_id (not including the version)
            2- version of the sequence (full id will be refseq_id.version)
            3- product protein description
            4- length (number of aa)
        it also returns a string with the refseq_id of the gene
        """
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
        transcript = cds.qualifiers['coded_by'][0].split(':')[0]
        if transcript.startswith("join("):
            transcript.strip("join(")
        xref = cds.qualifiers.get('db_xref', [])
        GeneID = [i.split(':')[-1] for i in xref if i.startswith('GeneID')][0]
        protein = Protein(refseq=withversion, ensembl=None, descr=descr, length=length, note=note)
        gene = Gene(GeneID=GeneID,
                    ensembl=None, symbol=cds.qualifiers.get('gene', [None])[0],
                    synonyms=cds.qualifiers.get('gene_synonym', [None])[0],
                    chromosome=None, strand=None)
        return protein, gene, transcript
