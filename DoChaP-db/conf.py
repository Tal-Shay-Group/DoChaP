# this is a configuration file for DoChaP database builder and its modules

# This are the species currently available by DoChaP:
all_species = ('D_rerio', 'R_norvegicus',  'X_tropicalis', 'M_musculus', 'H_sapiens')

# for ID converter builder
taxIDdict = {'M_musculus': 10090, 'H_sapiens': 9606, 'R_norvegicus': 10116, 'D_rerio': 7955,
             'X_tropicalis': 8364}

# for refseq builder
SpeciesConvertor = {'M_musculus': 'Mus_musculus', 'H_sapiens': 'Homo_sapiens',
                         'R_norvegicus': 'Rattus_norvegicus',
                         'D_rerio': 'Danio_rerio', 'X_tropicalis': 'Xenopus_tropicalis'}

speciesTaxonomy = {"Mus_musculus": "vertebrate_mammalian", "Homo_sapiens": "vertebrate_mammalian",
                                'Danio_rerio': "vertebrate_other", "Xenopus_tropicalis": "vertebrate_other",
                                "Rattus_norvegicus": "vertebrate_mammalian"}

# currently unsed
# ftpDirPath = {"Mus_musculus": "latest_assembly_versions", "Homo_sapiens": "latest_assembly_versions",
#               "Danio_rerio": "latest_assembly_versions",
#               "Xenopus_tropicalis": "representative", "Rattus_norvegicus": "representative"}

RefSeqGenomicVersion = {"Mus_musculus": "GCF_000001635.27_GRCm39",
                        "Homo_sapiens": "GCF_000001405.39_GRCh38.p13",
                        "Danio_rerio": "latest_assembly_versions",
                        "Xenopus_tropicalis": "GCF_000004195.4_UCB_Xtro_10.0",
                        "Rattus_norvegicus": "GCF_000001895.5_Rnor_6.0"}
isSupressed = {"Mus_musculus": False, "Homo_sapiens": False, "Danio_rerio": False,
               "Xenopus_tropicalis": False, "Rattus_norvegicus": True}
# for ensembl
SpConvert_EnsDomains = {'M_musculus': 'mmusculus', 'H_sapiens': 'hsapiens',
                                   'R_norvegicus': 'rnorvegicus', 'D_rerio': 'drerio',
                                   'X_tropicalis': 'xtropicalis'}
SpConvert_EnsBuilder = {'M_musculus': 'mus_musculus', 'H_sapiens': 'homo_sapiens',
                             'R_norvegicus': 'rattus_norvegicus', 'D_rerio': 'danio_rerio',
                             'X_tropicalis': 'xenopus_tropicalis'}
SpConvert_EnsShort = {'M_musculus': 'MUSG', 'H_sapiens': 'G', 'R_norvegicus': 'RNOG',
                                      'D_rerio': 'DARG', 'X_tropicalis': 'XETG'}
# Domains
supported_Prefix = {'cd': 'cd', 'pfam': 'pfam', 'pf': 'pfam',
                    'smart': 'smart', 'sm': 'smart', 'tigr': 'tigr', 'tigrfams': 'tigr',
                    'ipr': 'IPR', 'interpro': 'IPR'}  # 'cl': 'cl',
pref2Types = {"cd": "cdd", "IPR": "interpro", "tigr": "tigrfams",
              "pfam": "pfam", "smart": "smart"}  # "cl": "cdd",
external = ['cdd', 'pfam', 'smart', 'tigrfams', 'interpro']
