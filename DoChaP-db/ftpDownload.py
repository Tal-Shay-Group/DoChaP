import ftplib
import gzip
import os
import datetime


class ftpDownload:
    def __init__(self, species, ftp_adress, ftp_path, savePath, files2Download=None, specifyPathFunc=None,
                 username='anonymous', pswd='example@post.bgu.ac.il'):
        self.username = username
        self.pswd = pswd
        self.species = species
        self.ftp_address = ftp_adress
        self.ftp_path = ftp_path
        self.specifyPathFunc = specifyPathFunc
        self.savePath = savePath
        self.files2Download = files2Download

    def Download(self, extract=True, writeReadme=True):
        print('connecting to: ' + self.ftp_address + '...')
        ftp = ftplib.FTP(self.ftp_address)
        print('logging in...')
        ftp.login(user=self.username, passwd=self.pswd)
        ftp.cwd(self.ftp_path)
        if self.species is not None:
            print('Downloading files for - ' + self.species + '...')
        print('Downloading files from source : ' + ftp.pwd())
        print('Downloading files to : ' + self.savePath)
        filesInDir = ftp.nlst()
        if self.specifyPathFunc is None:
            downlist = self.files2Download
        else:
            downlist = self.specifyPathFunc(filesInDir)
        outlist = []
        for file in downlist:
            filePath = self.savePath + file[1]
            os.makedirs(os.path.dirname(filePath), exist_ok=True)
            print('downloading: ', file[0], '.gz ...')
            ftp.sendcmd("TYPE i")
            with open(filePath + '.gz', 'wb') as f:
                def callback(chunk):
                    f.write(chunk)
                ftp.retrbinary("RETR " + file[0] + '.gz', callback)
            if extract:
                print('extracting...')
                inp = gzip.GzipFile(filePath + '.gz', 'rb')
                s = inp.read()
                inp.close()
                with open(filePath, 'wb') as f_out:
                    f_out.write(s)
                print('removing compressed file...')
                os.remove(filePath + '.gz')
            outlist.append(filePath)
        if writeReadme:
            with open(os.path.dirname(self.savePath) + '/README.txt', 'a') as readme:
                print('Writing README description...')
                readme.write(
                    "=" * 10 + ' Updated on:{} '.format(str(datetime.datetime.now().date())) + "=" * 10 + '\n\n')
                readme.write('# FTP ADDRESS:\t' + self.ftp_address + self.ftp_path + '\n\n')
                readme.write('# DOWNLOADED FILES:\n')
                for file in downlist:
                    readme.write('\t' + file[0] + '\t\tSAVED AS:\t\t' + file[1] + '\n')
                    readme.write('\n')
                readme.write('# .gz files were extracted and removed\n\n')
        return outlist
