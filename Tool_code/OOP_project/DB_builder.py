from sqlite3 import connect
import Tool_code.ucscParser

from Tool_code import ffParser, ffDownloader, order_domains


def create_tables_db(species):
    """
    Create a transcripts table in the specie database and fills with ucsc transcripts data
    """
    db_name = 'DB_' + species
    print("Creating database: {}...".format(db_name))
    with connect(db_name + '.sqlite') as con:
        cur = con.cursor()
        cur.executescript('DROP TABLE IF EXISTS Genes;')
        print('Creating the table: Genes')
        cur.execute('''
                    CREATE TABLE Genes(
                            gene_id TEXT NOT NULL PRIMARY KEY UNIQUE,
                            gene_symbol TEXT,
                            synonyms TEXT,
                            chromosome TEXT,
                            strand TEXT,
                            MGI_id TEXT,
                            ensembl_id TEXT,
                            specie TEXT
                            );'''
                    )
        cur.executescript("DROP TABLE IF EXISTS transcripts;")
        print('Creating the table: Transcripts')
        cur.execute('''
                    CREATE TABLE Transcripts(
                            transcript_id TEXT NOT NULL PRIMARY KEY UNIQUE,
                            tx_start INTEGER,
                            tx_end INTEGER,
                            cds_start INTEGER,
                            cds_end INTEGER,
                            gene_id TEXT,                        
                            exon_count INTEGER,
                            ensembl_ID TEXT,
                            protein_id INTEGER,
                            FOREIGN KEY(gene_id) REFERENCES Genes(gene_id),
                            FOREIGN KEY(protein_id) REFERENCES Proteins(protein_id)
                            );'''
                    )
        cur.executescript("DROP TABLE IF EXISTS Exons;")
        print('Creating the table: Exons')
        cur.execute('''
                    CREATE TABLE Exons(
                            gene_id TEXT,        
                            genomic_start_tx INTEGER,
                            genomic_end_tx INTEGER,
                            PRIMARY KEY (gene_id, genomic_start_tx, genomic_end_tx),
                            FOREIGN KEY(gene_id) REFERENCES Genes(gene_id)
                            );'''
                    )

        cur.executescript("DROP TABLE IF EXISTS Transcript_Exon;")
        print('Creating the table: Transcript_Exon')
        cur.execute('''
                    CREATE TABLE Transcript_Exon(
                            transcript_id TEXT,
                            order_in_transcript INTEGER,
                            genomic_start_tx INTEGER,
                            genomic_end_tx INTEGER,
                            abs_start_CDS INTEGER,
                            abs_end_CDS INTEGER,
                            PRIMARY KEY(transcript_id, order_in_transcript),
                            FOREIGN KEY(transcript_id) REFERENCES Transcripts(transcript_id),
                            FOREIGN KEY(genomic_start_tx, genomic_end_tx)\
                             REFERENCES Exons(genomic_start_tx, genomic_end_tx)
                            );'''
                    )

        cur.executescript("DROP TABLE IF EXISTS Proteins;")
        print('Creating the table: Proteins')
        cur.execute('''
                    CREATE TABLE Proteins(
                            protein_id TEXT NOT NULL PRIMARY KEY UNIQUE,
                            description TEXT,
                            synonyms TEXT,
                            length INTEGER,
                            ensembl_id TEXT,
                            uniprot_id TEXT,
                            gene_id TEXT,
                            transcript_id TEXT,
                            FOREIGN KEY(gene_id) REFERENCES Genes(gene_id),
                            FOREIGN KEY(transcript_id) REFERENCES Transcripts(transcript_id)
                            );'''
                    )
        cur.executescript("DROP TABLE IF EXISTS DomainType;")
        print('Creating the table: DomainType')
        cur.execute('''
                    CREATE TABLE DomainType(
                            type_id INTEGER NOT NULL PRIMARY KEY UNIQUE,
                            name TEXT,
                            other_name TEXT,
                            description TEXT,
                            CDD_id TEXT,
                            cd TEXT,
                            cl TEXT,
                            pfam TEXT,
                            smart TEXT,
                            nf TEXT,
                            cog TEXT,
                            kog TEXT,
                            prk TEXT,
                            tigr TEXT,
                            other TEXT
                            );'''
                    )
        cur.executescript("DROP TABLE IF EXISTS DomainEvent;")
        print('Creating the table: DomainEvent')
        cur.execute('''
                    CREATE TABLE DomainEvent(
                            protein_id TEXT,
                            type_id INTEGER,
                            AA_start INTEGER,
                            AA_end INTEGER,
                            nuc_start INTEGER,
                            nuc_end INTEGER,
                            total_length INTEGER,
                            ext_id TEXT,
                            splice_junction BOOLEAN,
                            complete_exon BOOLEAN,
                            PRIMARY KEY(protein_id, type_id, AA_start, total_length, ext_id),
                            FOREIGN KEY(type_id) REFERENCES DomainType(type_id),
                            FOREIGN KEY(protein_id) REFERENCES Proteins(protein_id)
                            );'''
                    )
        cur.executescript("DROP TABLE IF EXISTS SpliceInDomains;")
        print('Creating the table: SpliceInDomains')
        cur.execute("""
                    CREATE TABLE SpliceInDomains(
                            transcript_id TEXT,
                            exon_order_in_transcript INTEGER,
                            type_id INTEGER,
                            total_length INTEGER,
                            domain_nuc_start INTEGER,
                            included_len INTEGER,
                            exon_num_in_domain INTEGER,
                            PRIMARY KEY (transcript_id, exon_order_in_transcript, type_id,\
                            total_length, domain_nuc_start),
                            FOREIGN KEY(transcript_id) REFERENCES Transcripts(transcript_id),
                            FOREIGN KEY(exon_order_in_transcript) REFERENCES Transcript_Exon(order_in_transcript),
                            FOREIGN KEY(type_id) REFERENCES DomainType(type_id),
                            FOREIGN KEY(domain_nuc_start, total_length) REFERENCES DomainEvent(Nuc_start, total_length)
                            );"""
                    )


def domain_exon_relationship(domain_nuc_positions, exon_starts, exon_ends):
    for ii in range(len(exon_starts)):
        if exon_starts[ii] <= domain_nuc_positions[0] <= exon_ends[ii]:
            if domain_nuc_positions[1] <= exon_ends[ii]:
                return 'complete_exon', ii + 1, domain_nuc_positions[1] - domain_nuc_positions[0] + 1
            else:
                flag = 0
                jj = ii + 1
                length = [-1 * (exon_ends[ii] - domain_nuc_positions[0] + 1)]
                while flag == 0 and jj < len(exon_starts):
                    if exon_starts[jj] <= domain_nuc_positions[1] <= exon_ends[jj]:
                        flag = 1
                        length.append(domain_nuc_positions[1] - exon_starts[jj] + 1)
                    else:
                        length.append(exon_ends[jj] - exon_starts[jj] + 1)
                    jj += 1
                return 'splice_junction', list(range(ii + 1, jj + 1)), length

    return None, None, None


