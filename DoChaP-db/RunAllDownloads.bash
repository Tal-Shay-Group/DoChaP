#!/bin/bash

chmod -R 770 *

# create the downloads shell scripts for ensembl domains and orthology from BioMart
#python CreateAllDownloadScripts.py

#FILE=ShellScripts.txt
#if test -f "$FILE"; then
#    echo "$FILE exists."
#else
#    echo "$FILE not found"
#    exit 1
#fi
#
#chmod -R 770 *
## Run the shell scripts
#while IFS='' read -r LINE || [ -n "$LINE" ]; do
#        qsub -cwd -q tals.q -V ${LINE}
#done < ShellScripts.txt
# Download all other data (ftp sites and interpro)
python DownloadAll.py
