import ftplib
import gzip
import os
import datetime
from Bio import SeqIO

from Tool_code.OOP_project.Director import SourceBuilder


class ffBuilder(SourceBuilder):
    """
    Download and parse Genebank flatfiles
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
        self.savePath = '/data/{}/flatfiles/'.format(self.species)
        # self.fileList = None
        self.fileList = [os.getcwd() + '\\data\\' + self.species + '\\flatfiles\\' + i for i in
                         os.listdir(os.getcwd() + '\\data\\' + self.species + '\\flatfiles\\') if i.endswith(".gpff")]

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
        download_path = self.savePath
        print('downloading files to : ' + self.savePath)
        gbff_files = []
        gpff_files = []
        for f in ftp.nlst():
            if 'gbff.gz' == f[-7:]:
                gbff_files.append((f, os.getcwd() + self.savePath + f[:-3]))
            elif 'gpff.gz' == f[-7:]:
                gpff_files.append((f, os.getcwd() + self.savePath + f[:-3]))
        # for file in gbff_files + gpff_files:
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
            for file in gbff_files + gpff_files:
                readme.write('\t' + file[0] + '\n')
                readme.write('\n')
            readme.write('# Files were extracted succsessfully!')
        self.setFileList([f[1] for f in gpff_files])

    def parser(self):
        regions = {}
        p_info = {}
        g_info = {}
        pro2gene = {}
        gene2pro = {}
        all_domains = set()
        kicked = []
        for file in self.fileList:
            reg, p, g, p2g, g2p, dom, kic = self.parse_gpff(file)
            regions.update(reg)
            p_info.update(p)
            g_info.update(g)
            pro2gene.update(p2g)
            gene2pro.update(g2p)
            all_domains = all_domains.union(dom)
            kicked = kicked + kic
        return regions, p_info, g_info, pro2gene, gene2pro, all_domains, kicked

    def parse_gpff(self, gpff_path):
        '''Parse protein data from all gbff files using Bio.SeqIO'''
        # records = []
        region_dict = {}
        p_info = {}
        g_info = {}
        all_domains = set()
        pro2gene = {}
        gene2pro = {}
        kicked = []
        for rec in SeqIO.parse(gpff_path, 'gb'):
            # records.append(rec)
            # rec.name is without version ; rec.id is with version
            # print(rec.id)
            if rec.name in p_info.keys():
                raise ('redundancy err ' + rec.name)
            if rec.name[0:2] == 'NP' or rec.name[0:2] == 'XP':  # takes both proteins and predictions!
                info, gene, gene_info = self.protein_info(rec)
                p_info[rec.name] = info[1:]
                genekey = gene.split('.')[0]
                g_info[genekey] = gene_info
                pro2gene[rec.name] = gene
                gene2pro[genekey] = rec.name
                rr, dd, kic = self.regions_from_record(rec)
                region_dict[rec.name] = rr
                all_domains = all_domains.union(dd)
                kicked = kicked + kic
        return region_dict, p_info, g_info, pro2gene, gene2pro, all_domains, kicked

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
        domains = set()
        kicked = []
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
                # cdId = note.split('; ')[-1]
                # print(name)
                if name.startswith('PRK'):
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
                        kicked.append(note)
                        continue
                    cdId = None
                    domains = domains.union({ext_id})
                else:
                    cdId = reg.qualifiers['db_xref'][0].split(':')[1]
                    domains = domains.union({cdId})
                parsed.append((start, end, name, note, ext_id, cdId))
        return parsed, domains, kicked

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
        refseq_id = record.name  # without version
        descr = record.description
        pro = [p for p in record.features if p.type == 'Protein'][0]
        length = pro.location.end.position  # length!!!
        try:
            note = pro.qualifiers['note'][0]
        except Exception:
            note = None
        cds = [c for c in record.features if c.type == 'CDS'][0]
        gene = cds.qualifiers['coded_by'][0].split(':')[0]
        gene_info = (cds.qualifiers.get('gene', [None])[0], cds.qualifiers.get('gene_synonym', [None])[0],
                     cds.qualifiers.get('db_xref', []))
        return (refseq_id, withversion, descr, length, note,), gene, gene_info

    def records(self):
        return self.parser()


# todo once:
def download_refseq_ensemble_connection(username='anonymous', pswd='example@post.bgu.ac.il'):
    ftp_address = 'ftp.ncbi.nlm.nih.gov'
    print('connecting to: ' + ftp_address + '...')
    ftp = ftplib.FTP(ftp_address)
    print('logging in...')
    ftp.login(user=username, passwd=pswd)
    ftp_path = '/gene/DATA/'
    ftp.cwd(ftp_path)
    download_path = os.getcwd() + '/data/'
    print('downloading files to : ' + download_path)
    os.makedirs(download_path, exist_ok=True)
    filename = 'gene2ensembl'
    print('downloading: ', filename, '...')
    ftp.sendcmd("TYPE i")
    # size = ftp.size(file[0])
    with open(download_path + filename + '.txt.gz', 'wb') as f:
        def callback(chunk):
            f.write(chunk)

        ftp.retrbinary("RETR " + filename + '.gz', callback)
    print('extracting...')
    inp = gzip.GzipFile(download_path + filename + '.txt.gz', 'rb')
    s = inp.read()
    inp.close()
    with open(download_path + filename + '.txt', 'wb') as f_out:
        f_out.write(s)
    print('removing compressed file...')
    os.remove(download_path + filename + '.txt.gz')


def gene2ensembl_parser(specie, filelocation=os.getcwd() + '/data/'):
    '''
    This function uses the table gene2ensembl from refseq database to create all connections
    between RefSeq and ENSEMBL for gene, transcript, protein
    Table columns: table columns:
    taxID;geneID;ENS_GeneID;refseq_transcript;ENS_transcript;refseq_protein;ENS_protein
    '''
    taxID = {'M_musculus': 10090, 'H_sapiens': 9606, 'R_norvegicus': 10116, 'D_rerio': 7955, 'X_tropicalis': 8364}
    # print(taxID[specie])
    tablename = 'gene2ensembl.txt'
    gene_con = {}
    trans_con = {}
    protein_con = {}
    with open(filelocation + tablename, 'r') as g2e:
        for line in g2e:
            ll = line.strip().split('\t')
            # print(ll)
            if ll[0] == str(taxID[specie]):
                # print(ll[0])
                gene_con[ll[1]] = gene_con.get(ll[1], ll[2])
                trans_con[ll[3]] = ll[4]
                protein_con[ll[5]] = ll[6]
    return gene_con, trans_con, protein_con
