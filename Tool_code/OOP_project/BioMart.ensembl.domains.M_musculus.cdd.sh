#!/bin/sh

wget -O C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP\Tool_code\OOP_project/data/M_musculus/ensembl/BioMart/M_musculus.Domains.cdd.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >

  <Dataset name = "mmusculus_gene_ensembl_gene_ensembl" interface = "default" >
    <Attribute name = "ensembl_transcript_id_version" />
    <Attribute name = "ensembl_peptide_id_version" />
    <Attribute name = "interpro" />
    <Attribute name = "interpro_short_description" />
    <Attribute name = "interpro_description" />
    <Attribute name = "interpro_start" />
    <Attribute name = "interpro_end" />
    <Attribute name = "cdd" />
    <Attribute name = "cdd_start" />
    <Attribute name = "cdd_end" />
  </Dataset>
</Query>'
