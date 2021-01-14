# this is a configuration file for DoChaP database builder and its modules

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

ftpDirPath = {"Mus_musculus": "latest_assembly_versions", "Homo_sapiens": "latest_assembly_versions",
              "Danio_rerio": "latest_assembly_versions",
              "Xenopus_tropicalis": "representative", "Rattus_norvegicus": "representative"}

# for ensembl
speciesConvertor_Ensembl = {'M_musculus': 'mmusculus', 'H_sapiens': 'hsapiens',
                            'R_norvegicus': 'rnorvegicus', 'D_rerio': 'drerio',
                            'X_tropicalis': 'xtropicalis'}

# Domains
supported_Prefix = {'cd': 'cd', 'cl': 'cl', 'pfam': 'pfam', 'pf': 'pfam',
                    'smart': 'smart', 'sm': 'smart', 'tigr': 'tigr', 'tigrfams': 'tigr',
                    'ipr': 'IPR', 'interpro': 'IPR'}
pref2Types = {"cd": "cdd", "cl": "cdd", "IPR": "interpro", "tigr": "tigrfams",
              "pfam": "pfam", "smart": "smart"}
external = ['cdd', 'pfam', 'smart', 'tigrfams', 'interpro']