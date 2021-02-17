#!/bin/bash

chmod -R 770 *

# create the downloads shell scripts for ensembl domains and orthology from BioMart
python CreateAlDownloadScripts.py
# Run the shell scripts
while IFS='' read -r LINE || [ -n "$LINE" ]; do
        qsub -cwd -q tals.q -V ${LINE}
done < ShellScripts.txt
# Download all other data (ftp sites and interpro)
python DownloadAll.py
