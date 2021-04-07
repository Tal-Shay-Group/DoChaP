from sqlite3 import connect
import pandas as pd
import numpy as np

savingPath = r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP\DoChaP-db\dbs\csv_tables'
dbName = r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP\DoChaP-web\DB_merged.sqlite'
with connect(dbName) as con:
    all_transcripts_genes = pd.read_sql('''SELECT Genes.gene_GeneID_id, Genes.gene_ensembl_id, gene_symbol, specie, 
    Transcripts.transcript_refseq_id, Transcripts.transcript_ensembl_id, Transcripts.protein_refseq_id, 
    Transcripts.protein_ensembl_id
    from Genes
    inner join Transcripts on 
    ((Genes.gene_GeneID_id == Transcripts.gene_GeneID_id) or
    (Genes.gene_ensembl_id == Transcripts.gene_ensembl_id))''', con)

    # domainEvent = pd.read_sql('''select * from DomainEvent''', con)
    # domainType = pd.read_sql('''select * from DomainType''', con)
    AllDomains = pd.read_sql('''select DomainEvent.type_id, protein_refseq_id, protein_ensembl_id, name, ext_id,
    AA_start, AA_end, nuc_start, nuc_end
    from DomainEvent join DomainType on DomainEvent.type_id == DomainType.type_id''', con)


def myf(x):
    n = 0
    for y in x:
        tmp = y.split("|")
        if n == 0:
            newOut = [[v.replace(",", ".")] for v in tmp]
            n += 1
        else:
            for i in range(len(tmp)):
                newOut[i].append(tmp[i])
    newOut = "||".join([";".join([v[1], v[2], v[3] + "-" + v[4], v[5] + "-" + v[6]]) for v in newOut])
    return newOut


# handle transcript&genes table
dupT = all_transcripts_genes["transcript_ensembl_id"].duplicated() & all_transcripts_genes[
    "transcript_ensembl_id"].notna()
dupT = ~dupT
all_transcripts_genes = all_transcripts_genes[dupT]
all_transcripts_genes = all_transcripts_genes.replace(np.nan, '', regex=True)

# handle domain table
AllDomains = AllDomains.replace(np.nan, '', regex=True)
AllDomains['ext_id'] = AllDomains['ext_id'].str.replace("; ", "/")
sgr = AllDomains.groupby(['protein_refseq_id', 'protein_ensembl_id']).agg(
    lambda x: "|".join(str(y).replace(",", ".") for y in list(x)))
sgr = sgr.apply(myf, axis=1, result_type="expand")
sgr = sgr.reset_index()
sgr.columns = ['protein_refseq_id', 'protein_ensembl_id', 'Domains_info']

# merge data
totalData = all_transcripts_genes.merge(sgr, on=['protein_refseq_id', 'protein_ensembl_id'], how="outer")
totalData.columns = ['gene-GeneID_id', 'gene-ensembl_id', 'gene_symbol', 'species',
                     'transcript-refseq_id', 'transcript-ensembl_id', 'protein-refseq_id',
                     'protein-ensembl_id', 'domains_info']
# save all
totalData.to_csv(savingPath + "/All_species_transcript_domainsInfo.csv")
totalData[0:50].to_csv(savingPath + "/All_species_transcript_domainsInfo_50.csv")

species = ('H_sapiens', 'M_musculus', 'D_rerio', 'R_norvegicus', 'X_tropicalis')
for sp in species:
    currDf = totalData[totalData["species"] == sp]
    currDf.to_csv(savingPath + "/{}_transcript_domainsInfo.csv".format(sp), index=False)
