import ftplib
import gzip
import os
import datetime
import time
import datetime
import shutil
from pathlib import Path

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
        print("ftpDwonload:", self.username, self.pswd,  self.species , self.ftp_address, self.ftp_path ,  self.specifyPathFunc, self.savePath , self.files2Download)

    def Download(self, extract=True, writeReadme=True):
        print("Download: ====================================================================================")
        for i in range(10):
            ok, to_return = self.Download_trial(extract, writeReadme)
            if ok:
                print("Succeed:downloading ====================================================================================")
                return to_return
            time.sleep(1)
        print("Error: ftp failed")
        print("====================================================================================")
        exit(1)

    def Download_trial(self, extract=True, writeReadme=True):
        outlist = []
        # Use context manager for FTP to ensure connection closes
        try:
            print(f"Connecting to {self.ftp_address}...")
            with ftplib.FTP(self.ftp_address, timeout=600) as ftp:
                ftp.login(user=self.username, passwd=self.pswd)
                ftp.cwd(self.ftp_path)
                ftp.set_pasv(True)

                files_in_dir = ftp.nlst()
                downlist = self.files2Download if self.specifyPathFunc is None else self.specifyPathFunc(files_in_dir)

                for remote_name, local_rel_path in downlist:
                    # Use Path for cleaner path handling
                    local_path = Path(self.savePath) / local_rel_path
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    gz_path = local_path.with_suffix(local_path.suffix + '.gz')
                    success = False

                    for attempt in range(1, 11): # 10 retries
                        try:
                            print(f"Downloading {remote_name}.gz (Attempt {attempt})...")
                            with open(gz_path, 'wb') as f:
                                ftp.retrbinary(f"RETR {remote_name}.gz", f.write)

                            if extract:
                                print(f"Extracting to {local_path}...")
                                with gzip.open(gz_path, 'rb') as f_in:
                                    with open(local_path, 'wb') as f_out:
                                        shutil.copyfileobj(f_in, f_out)
                                gz_path.unlink() # Delete .gz file

                            outlist.append(str(local_path))
                            success = True
                            break
                        except Exception as e:
                            print(f"\tError: {e}. Retrying...")

                if not success:
                    print(f"Failed to download {remote_name} after 10 attempts.")
                    return 0, []

            if writeReadme:
                self._write_readme(downlist)

            return 1, outlist

        except Exception as e:
            print(f"FTP Error: {e}")
            return 0, []

    def _write_readme(self, downlist):
        readme_path = Path(self.savePath).parent / "README.txt"
        with open(readme_path, 'a') as f:
            f.write(f"\n{'='*10} Updated on: {datetime.date.today()} {'='*10}\n")
            f.write(f"FTP ADDRESS: {self.ftp_address}{self.ftp_path}\n")
            f.write("DOWNLOADED FILES:\n")
            for remote, local in downlist:
                f.write(f"\t{remote}\tSAVED AS:\t{local}\n")

