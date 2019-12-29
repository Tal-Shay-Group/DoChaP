# -*- coding: utf-8 -*-
"""
Download files from refseq ftp site
Created on Tue Jun 18 15:34:18 2019

@author: galozs
"""
'''TODO
make generic for other species implementation
'''

import ftplib
import gzip
import os
import datetime






def validate_specie(specie):
    ff_conversion = {'mouse': 'M_musculus', 'm_musculus': 'M_musculus', 'mus_musculus': 'M_musculus', 'mm10': 'M_musculus',
                 'human':'H_sapiens', 'h_sapiens': 'H_sapiens', 'r_norvegicus':'R_norvegicus',
                 'd_rerio':'D_rerio', 'x_tropicalis':'X_tropicalis'}
    if specie.lower() in ff_conversion.keys():
        return ff_conversion[specie.lower()]
    else:
        raise ValueError('Unrecognized specie: ' + specie)
        
        

def download_flatfiles(specie, username='anonymous',pswd = 'example@post.bgu.ac.il'):
    skey = validate_specie(specie)
    ftp_address = 'ftp.ncbi.nlm.nih.gov'
    print('connecting to: '+ ftp_address + '...')
    ftp = ftplib.FTP(ftp_address)
    print('logging in...')
    ftp.login(user = username, passwd=pswd)
    ftp_path = '/refseq/{}/mRNA_Prot/'
    ftp.cwd(ftp_path.format(skey))
    print('looking for gbff and gpff files for specie - ' + specie + '...')
    download_path = '/data/{}/flatfiles/'
    print('downloading files to : ' + download_path.format(skey))
    gbff_files = []
    gpff_files = []
    for f in ftp.nlst():
        if 'gbff.gz' == f[-7:] :
            gbff_files.append((f, os.getcwd() + download_path.format(skey) + f[:-3]))
        elif 'gpff.gz' == f[-7:] :
            gpff_files.append((f, os.getcwd() + download_path.format(skey) + f[:-3]))
    #for file in gbff_files + gpff_files:
    for file in gpff_files: # Currently ignoring gbff as it is not used
        os.makedirs(os.path.dirname(file[1]), exist_ok=True)
        print('downloading: ',file[0],'...')
        ftp.sendcmd("TYPE i")
        #size = ftp.size(file[0])
        with open(file[1] + '.gz','wb') as f:
            def callback(chunk):
                f.write(chunk)
            ftp.retrbinary("RETR " + file[0], callback)
        print('extracting...')
        inp = gzip.GzipFile(file[1] + '.gz', 'rb')
        s =  inp.read()
        inp.close()
        with open(file[1] ,'wb') as f_out:
            f_out.write(s)
        print('removing compressed file...')
        os.remove(file[1] + '.gz')
    with open(os.path.dirname(file[1]) + '/README.txt', 'w') as readme:
        print('Writing README description...')
        readme.write('# Updated on: ' + str(datetime.datetime.now().date()) + '\n\n')
        readme.write('# Files were downloaded from:\t' + ftp_address + ftp_path +'\n\n')
        readme.write('# List of downloaded files:\n')
        for file in gbff_files + gpff_files:
            readme.write('\t' + file[0] + '\n')
            readme.write('\n')
        readme.write('# Files were extracted succsessfully!')
    return gbff_files, gpff_files


def download_refseq_ensemble_connection(username='anonymous',pswd = 'example@post.bgu.ac.il'):
    ftp_address = 'ftp.ncbi.nlm.nih.gov'
    print('connecting to: '+ ftp_address + '...')
    ftp = ftplib.FTP(ftp_address)
    print('logging in...')
    ftp.login(user = username, passwd=pswd)
    ftp_path = '/gene/DATA/'
    ftp.cwd(ftp_path)
    download_path = os.getcwd() + '/data/'
    print('downloading files to : ' + download_path)
    os.makedirs(download_path, exist_ok=True)
    filename = 'gene2ensembl'
    print('downloading: ',filename,'...')
    ftp.sendcmd("TYPE i")
    #size = ftp.size(file[0])
    with open(download_path + filename + '.txt.gz','wb') as f:
        def callback(chunk):
            f.write(chunk)
        ftp.retrbinary("RETR " + filename + '.gz', callback)
    print('extracting...')
    inp = gzip.GzipFile(download_path + filename + '.txt.gz', 'rb')
    s =  inp.read()
    inp.close()
    with open(download_path + filename + '.txt' ,'wb') as f_out:
        f_out.write(s)
    print('removing compressed file...')
    os.remove(download_path + filename + '.txt.gz')
    
    
def download_ucsc_tables(specie, username='anonymous',pswd = 'example@post.bgu.ac.il'):
    table_key = validate_specie(specie)
    ucsc_conversion = {'M_musculus': 'mm10', 'H_sapiens':'hg38', 'R_norvegicus':'rn6', 'D_rerio': 'danRer11', 'X_tropicalis':'xenTro9'}
    skey = ucsc_conversion[table_key]
    
    ftp_address = 'hgdownload.soe.ucsc.edu'
    print('connecting to: '+ ftp_address + '...')
    ftp = ftplib.FTP(ftp_address)
    print('logging in...')
    ftp.login(user = username, passwd=pswd)
    ftp_path = '/goldenPath/{}/database/'
    ftp.cwd(ftp_path.format(skey))
    download_path = os.getcwd() + '/data/{}/from_ucsc/'
    print('downloading files to : ' + download_path.format(table_key))            
    os.makedirs(os.path.dirname(download_path.format(table_key)), exist_ok=True)
    tables = ['refGene', 'kgXref', 'knownGene', 'ncbiRefSeq']
    allTables = ftp.nlst()
    for table in tables:
        if table + '.txt.gz' not in allTables:
            print('Table ' + table + ' not exist for species: ' + specie)
            continue
        table_path = download_path.format(table_key) + table + '.txt'
        print('downloading: ' + table + '.txt.gz..')
        ftp.sendcmd("TYPE i")
        with open(table_path + '.gz','wb') as f:
            def callback(chunk):
                f.write(chunk)
            ftp.retrbinary("RETR " + table + '.txt.gz', callback)
        print('extracting...')
        inp = gzip.GzipFile(table_path + '.gz', 'rb')
        s =  inp.read()
        inp.close()
        with open(table_path ,'wb') as f_out:
            f_out.write(s)
        print('removing compressed file...')
        os.remove(table_path + '.gz')
