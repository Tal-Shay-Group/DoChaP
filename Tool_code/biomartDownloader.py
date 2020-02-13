from pybiomart import Dataset
import os


def download_domains_BioMart(specie, ifsave=True):
    conversion = {'M_musculus': 'mmusculus_gene_ensembl', 'H_sapiens': 'hsapiens_gene_ensembl',
                  'R_norvegicus': 'rnorvegicus_gene_ensembl', 'D_rerio': 'drerio_gene_ensembl',
                  'X_tropicalis': 'xtropicalis_gene_ensembl'}
    dataset = Dataset(name=conversion[specie], host='http://www.ensembl.org')
    attributes = ["ensembl_gene_id_version", "ensembl_transcript_id_version", "cdd", "cdd_start", "cdd_end",
                  "pfam", "pfam_start", "pfam_end", "smart", "smart_start", "smart_end",
                  "tigrfam", "tigrfam_start", "tigrfam_end",
                  "interpro", "interpro_short_description", "interpro_start", "interpro_end",
                  "ensembl_peptide_id_version", "external_gene_name", "refseq_mrna"]
    data = dataset.query(attributes=attributes, only_unique=True)
    if not ifsave:
        return data
    else:
        path2save = os.getcwd() + 'data/{}/BioMart/'
        os.makedirs(os.path.dirname(path2save.format(specie)), exist_ok=True)
        data.to_csv(path2save.format(specie) + specie + '.Ensembl.Domains.csv', header=True)


#download_domains_BioMart('M_musculus')


#def parse_domain_BioMart(BMdataset):