#!/bin/bash

chmod -R 770 *

python CreateAlDownloadScripts.py

while IFS='' read -r LINE || [ -n "$LINE" ]; do
        qsub -cwd -q tals.q -V ${LINE}
done < ShellScripts.txt

python DownloadAll.py
