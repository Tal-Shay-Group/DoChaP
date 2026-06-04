from sqlite3 import connect
import pandas as pd
import numpy as np

dbName = r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP\DoChaP-db\dbs\15102020\DB_merged.sqlite'
with connect(dbName) as con:
    genes_c = pd.read_sql('''select specie, count(*) from Genes group by specie''', con, index_col = "specie")
    genes_c.columns = ["Genes_c"]
    # transcripts count
    transcripts_c = pd.read_sql('''
                    SELECT specie, count(*) 
                    FROM (SELECT * FROM 
                    (SELECT transcript_refseq_id, transcript_ensembl_id, G.specie FROM Transcripts
                    JOIN Genes G on (Transcripts.gene_ensembl_id = G.gene_ensembl_id)) as "T1"
                    UNION 
                    SELECT transcript_refseq_id, transcript_ensembl_id, G.specie
                    FROM Transcripts
                    JOIN Genes G on (Transcripts.gene_GeneID_id = G.gene_GeneID_id))
                    group by specie;
                    ''', con, index_col = "specie")
    transcripts_c.columns = ["Transcripts_c"]
    exons = pd.read_sql('''
                        select specie, count(*) from (
                         select Exons.gene_GeneID_id, Exons.gene_ensembl_id, Exons.genomic_end_tx, Exons.genomic_start_tx, G.specie
                         from Exons
                         JOIN Genes G on Exons.gene_GeneID_id = G.gene_GeneID_id
                         Union
                         select Exons.gene_GeneID_id, Exons.gene_ensembl_id, Exons.genomic_end_tx, Exons.genomic_start_tx, G2.specie
                         from Exons
                         JOIN Genes G2 on Exons.gene_ensembl_id = G2.gene_ensembl_id)
                         group by specie
                         ''', con, index_col = "specie")
    exons.columns = ["Exons_c"]
    DomainEvents = pd.read_sql('''Select * from DomainEvent''', con)
    DomainType = pd.read_sql('''select * from DomainType''', con)
    Genes = pd.read_sql('''select * from Genes''', con)
    Transcripts = pd.read_sql('''select * from Transcripts''', con)
    Splice_in_domain = pd.read_sql('''select * from SpliceInDomains''', con)


#merge pd
all = genes_c.merge(transcripts_c, left_index=True, right_index=True)
all = all.merge(exons, left_index=True, right_index=True)

speciesDict = {}
transcriptSpecies = {}
proteinSpecies = {}
Domainevent_c = {}
DomainType_c = {}
SpliceJ = {}
for sp in Genes.specie.unique():
    sdf = Genes[Genes.specie == sp]
    speciesDict[sp] = set(list(sdf.gene_GeneID_id) + list(sdf.gene_ensembl_id))
    speciesDict[sp].remove(None)
    spt = Transcripts[Transcripts['gene_GeneID_id'].isin(speciesDict[sp]) | Transcripts['gene_ensembl_id'].isin(speciesDict[sp])]

    transcriptSpecies[sp] = set(list(spt.transcript_refseq_id) + list(spt.transcript_ensembl_id))
    transcriptSpecies[sp].remove(None)
    proteinSpecies[sp] = set(list(spt.protein_refseq_id) + list(spt.protein_ensembl_id))
    proteinSpecies[sp].remove(None)
    domdf = DomainEvents[DomainEvents['protein_refseq_id'].isin(proteinSpecies[sp]) | DomainEvents['protein_ensembl_id'].isin(proteinSpecies[sp])]
    Domainevent_c[sp] = domdf.shape[0]
    DomainType_c[sp] = len(domdf.type_id.unique())

    Splicedf = Splice_in_domain[Splice_in_domain['transcript_refseq_id'].isin(transcriptSpecies[sp]) | Splice_in_domain['transcript_ensembl_id'].isin(transcriptSpecies[sp])]
    SpliceJ[sp] = Splicedf.shape[0]


all = all.merge(pd.DataFrame.from_dict(DomainType_c, orient='index'),  left_index=True, right_index=True)
all = all.merge(pd.DataFrame.from_dict(Domainevent_c, orient='index'),  left_index=True, right_index=True)
all = all.merge(pd.DataFrame.from_dict(SpliceJ, orient='index'),  left_index=True, right_index=True)

all.columns = ["Gene IDs", "  Transcript- isoform pairs", "Unique exons", "Protein domains", "Domain occurrences", "In-Domain Junction "]

all.to_csv(r"C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\Paper_tool\DB_content_Dec2020.csv")