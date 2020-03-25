import ftplib
import gzip
import os
import datetime
from Bio import SeqIO
import re
from OOP_project.recordTypes import *
from OOP_project.Director import SourceBuilder


class ffBuilder(SourceBuilder):
    """
    Download and parse Genebank flatfiles
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
        self.savePath = '/data/{}/flatfiles/'.format(self.species)
        self.fileList = [os.getcwd() + self.savePath + i for i in
                         os.listdir(os.getcwd() + self.savePath) if i.endswith(".gpff")]
        self.trans2pro = dict()
        self.pro2trans = dict()
        self.genes = dict()
        self.proteins = dict()
        self.domains = dict()
        self.ignoredDomains = dict()

    def setFileList(self, fileList):
        self.fileList = fileList

    def downloader(self):
        username = 'anonymous'
        pswd = 'example@post.bgu.ac.il'
        skey = self.species
        ftp_address = 'ftp.ncbi.nlm.nih.gov'
        print('connecting to: ' + ftp_address + '...')
        ftp = ftplib.FTP(ftp_address)
        print('logging in...')
        ftp.login(user=username, passwd=pswd)
        ftp_path = '/refseq/{}/mRNA_Prot/'
        ftp.cwd(ftp_path.format(skey))
        print('looking for gbff and gpff files for specie - ' + self.species + '...')
        print('downloading files to : ' + self.savePath)
        #gbff_files = []
        gpff_files = []
        for f in ftp.nlst():
            #if 'gbff.gz' == f[-7:]:
                #gbff_files.append((f, os.getcwd() + self.savePath + f[:-3]))
            if 'gpff.gz' == f[-7:]:
                gpff_files.append((f, os.getcwd() + self.savePath + f[:-3]))
        for file in gpff_files:  # Currently ignoring gbff as it is not used
            os.makedirs(os.path.dirname(file[1]), exist_ok=True)
            print('downloading: ', file[0], '...')
            ftp.sendcmd("TYPE i")
            # size = ftp.size(file[0])
            with open(file[1] + '.gz', 'wb') as f:
                def callback(chunk):
                    f.write(chunk)
                ftp.retrbinary("RETR " + file[0], callback)
            print('extracting...')
            inp = gzip.GzipFile(file[1] + '.gz', 'rb')
            s = inp.read()
            inp.close()
            with open(file[1], 'wb') as f_out:
                f_out.write(s)
            print('removing compressed file...')
            os.remove(file[1] + '.gz')
        with open(os.path.dirname(file[1]) + '/README.txt', 'w') as readme:
            print('Writing README description...')
            readme.write('# Updated on: ' + str(datetime.datetime.now().date()) + '\n\n')
            readme.write('# Files were downloaded from:\t' + ftp_address + ftp_path + '\n\n')
            readme.write('# List of downloaded files:\n')
            for file in gpff_files:
                readme.write('\t' + file[0] + '\n')
                readme.write('\n')
            readme.write('# Files were extracted succsessfully!')
        self.setFileList([f[1] for f in gpff_files])

    def parser(self):
        for file in self.fileList:
            for rec in SeqIO.parse(file, 'gb'):
                #if rec.name in self.proteins.keys():
                    #print(rec.name)
                if rec.name[0:2] == 'NP' or rec.name[0:2] == 'XP':  # takes both proteins and predictions!
                    protein, gene, transcript = self.protein_info(rec)
                    transcriptKey = transcript.split('.')[0]
                    regions = self.regions_from_record(rec)
                    self.domains[rec.name] = regions
                    self.proteins[rec.name] = protein
                    self.genes[transcriptKey] = gene
                    self.pro2trans[rec.name] = transcript
                    self.trans2pro[transcriptKey] = protein.refseq

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
        xref = cds.qualifiers.get('db_xref', [])
        GeneID = [i.split(':')[-1] for i in xref if i.startswith('GeneID')][0]
        protein = Protein(refseq=withversion, ensembl=None, descr=descr, length=length, note=note)
        gene = Gene(GeneID=GeneID,
                    ensembl=None, symbol=cds.qualifiers.get('gene', [None])[0],
                    synonyms=cds.qualifiers.get('gene_synonym', [None])[0],
                    chromosome=None, strand=None)
        return protein, gene, transcript


