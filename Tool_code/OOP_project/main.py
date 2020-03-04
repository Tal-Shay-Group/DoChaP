from Director import *
from UcscBuilder import *
from ffBuilder import *
from SpeciesDB import *

species = 'M_musculus'
ucscbuilder = UcscBuilder(species)
ffbuilder = ffBuilder(species)

director = Director()

director.setBuilder(ucscbuilder)
refGene, ucsc_acc = director.collectFromSource()

director.setBuilder(ffbuilder)
#ff = director.collectFromSource()

#download_refseq_ensemble_connection()
region_dict, p_info, g_info, pro2gene, gene2pro, all_domains, kicked = director.collectFromSource()
gene_con, trans_con, protein_con = gene2ensembl_parser(species)

dbBuild = dbBuilder(species, merged=False)
dbBuild.create_tables_db()
dbBuild.fill_in_db()








