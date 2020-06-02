#!/bin/sh

wget -O Pathspecies.Domains.interpro.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >

  <Dataset name = "EnsSpecies_gene_ensembl" interface = "default" >
    <Attribute name = "ensembl_transcript_id_version" />
    <Attribute name = "ensembl_peptide_id_version" />
    <Attribute name = "interpro" />
    <Attribute name = "interpro_short_description" />
    <Attribute name = "interpro_description" />
    <Attribute name = "interpro_start" />
    <Attribute name = "interpro_end" />
  </Dataset>
</Query>'

wget -O Pathspecies.Domains.cdd.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >

  <Dataset name = "EnsSpecies_gene_ensembl" interface = "default" >
    <Attribute name = "ensembl_transcript_id_version" />
    <Attribute name = "ensembl_peptide_id_version" />
    <Attribute name = "cdd" />
    <Attribute name = "cdd_start" />
    <Attribute name = "cdd_end" />
  </Dataset>
</Query>'

wget -O Pathspecies.Domains.pfam.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >

  <Dataset name = "EnsSpecies_gene_ensembl" interface = "default" >
    <Attribute name = "ensembl_transcript_id_version" />
    <Attribute name = "ensembl_peptide_id_version" />
    <Attribute name = "pfam" />
    <Attribute name = "pfam_start" />
    <Attribute name = "pfam_end" />
  </Dataset>
</Query>'

wget -O Pathspecies.Domains.smart.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >

  <Dataset name = "EnsSpecies_gene_ensembl" interface = "default" >
    <Attribute name = "ensembl_transcript_id_version" />
    <Attribute name = "ensembl_peptide_id_version" />
    <Attribute name = "smart" />
    <Attribute name = "smart_start" />
    <Attribute name = "smart_end" />
  </Dataset>
</Query>'

wget -O Pathspecies.Domains.tigrfam.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >

  <Dataset name = "EnsSpecies_gene_ensembl" interface = "default" >
    <Attribute name = "ensembl_transcript_id_version" />
    <Attribute name = "ensembl_peptide_id_version" />
    <Attribute name = "tigrfam" />
    <Attribute name = "tigrfam_start" />
    <Attribute name = "tigrfam_end" />
  </Dataset>
</Query>'