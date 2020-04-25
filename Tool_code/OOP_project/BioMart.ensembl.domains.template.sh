#!/bin/sh

wget -O output.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >

  <Dataset name = "MainSpecies_gene_ensembl" interface = "default" >
    <Attribute name = "ensembl_transcript_id_version" />
    <Attribute name = "ensembl_peptide_id_version" />
    <Attribute name = "extDB" />
    <Attribute name = "extDB_start" />
    <Attribute name = "extDB_end" />
  </Dataset>
</Query>'
