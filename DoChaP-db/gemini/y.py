import gffutils
db_temp = './h_sapiens_refseq.db'
gff_path = './genomic_data/H_sapiens/refseq/GCF_000001405.40_GRCh38.p14_genomic.gff'
print(f'Starting: {db_temp}, {gff_path}')
db = gffutils.create_db(gff_path, dbfn=db_temp , force=True, merge_strategy='merge', keep_order=True)
print('Done')
