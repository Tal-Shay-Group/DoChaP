import sys
import os
sys.path.append(os.getcwd())
from DomainsEnsemblBuilder import *

species = ['M_musculus', 'H_sapiens', 'R_norvegicus', 'D_rerio', 'X_tropicalis']
for sp in species:
    ens = DomainsEnsemblBuilder(sp, download=True)
    ens.downloader
    print("finish download for {}".format(sp))
