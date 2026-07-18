import re
import gzip
import datetime
import time
import shutil
import urllib.request
import urllib.error
from pathlib import Path


def validate_downloaded_file(path, valid_prefixes, label="file"):
    """Guard against silently-saved error pages.

    A download that returns HTTP 200 with an error/redirect body (e.g. an HTML
    'Service unavailable' page) is written to disk like a normal file and only
    blows up later during parsing. This checks the first non-empty line of a
    downloaded file against the prefix(es) a valid file must start with, and
    deletes + raises on a mismatch so the failure is loud and no bad file is
    left cached on disk.

    @param valid_prefixes: a string or iterable of strings; the file is valid
                           if its first line starts with any of them.
    """
    if isinstance(valid_prefixes, str):
        valid_prefixes = (valid_prefixes,)
    try:
        with open(path, 'r', errors='replace') as f:
            first = f.readline().lstrip()
    except OSError as e:
        raise RuntimeError("Expected downloaded {} not found at {}: {}".format(label, path, e))
    if not any(first.startswith(p) for p in valid_prefixes):
        preview = first[:120].rstrip()
        try:
            Path(path).unlink()  # never leave a bad file cached
        except OSError:
            pass
        raise RuntimeError(
            "Downloaded {} at {} is not valid (starts with {!r}, expected one of {}). "
            "It is most likely an error/redirect page saved during a download outage; "
            "the bad file was deleted, please re-run.".format(label, path, preview, list(valid_prefixes)))


class httpsDownload:
    """HTTPS counterpart to ftpDownload, kept API-compatible.

    Useful when the host also mirrors its FTP tree over HTTPS (e.g. EBI),
    which avoids the passive-mode data-connection port being blocked by
    cluster/compute-node firewalls.
    """

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
        self.base_url = f"https://{ftp_adress}{ftp_path}/"
        print("httpsDownload:", self.username, self.pswd, self.species, self.ftp_address, self.ftp_path,
              self.specifyPathFunc, self.savePath, self.files2Download)

    def Download(self, extract=True, writeReadme=True):
        print("Download: ====================================================================================")
        for i in range(10):
            ok, to_return = self.Download_trial(extract, writeReadme)
            if ok:
                print("Succeed:downloading ====================================================================================")
                return to_return
            time.sleep(1)
        print("Error: https download failed")
        print("====================================================================================")
        exit(1)

    def _list_dir(self):
        """Parses the Apache/nginx-style autoindex page into bare entry names.

        Mirrors ftplib's nlst(): returns file/directory names with no trailing
        slash and without parent-directory ('../'), absolute, or column-sort
        query links, so specifyPathFunc callers written for ftpDownload work
        unchanged.
        """
        with urllib.request.urlopen(self.base_url, timeout=600) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        names = []
        for href in re.findall(r'href="([^"]+)"', html):
            if href.startswith(('/', '?', '#')) or '://' in href or href.startswith('..'):
                continue
            name = href.rstrip('/')  # directory links carry a trailing slash
            if name and name not in names:
                names.append(name)
        return names

    def Download_trial(self, extract=True, writeReadme=True):
        # Kept byte-for-byte in step with ftpDownload.Download_trial: the caller
        # passes the remote name WITHOUT the .gz suffix (appended here), and
        # local_rel_path is the extracted name. Only the transport differs
        # (HTTPS GET instead of FTP RETR).
        outlist = []
        try:
            print(f"Connecting to {self.ftp_address}...")
            if self.specifyPathFunc is None:
                downlist = self.files2Download
            else:
                downlist = self.specifyPathFunc(self._list_dir())

            for remote_name, local_rel_path in downlist:
                local_path = Path(self.savePath) / local_rel_path
                local_path.parent.mkdir(parents=True, exist_ok=True)

                gz_path = local_path.with_suffix(local_path.suffix + '.gz')
                success = False

                for attempt in range(1, 11):  # 10 retries
                    try:
                        print(f"Downloading {remote_name}.gz (Attempt {attempt})...")
                        remote_url = self.base_url + remote_name + '.gz'
                        with urllib.request.urlopen(remote_url, timeout=600) as resp, \
                                open(gz_path, 'wb') as f:
                            shutil.copyfileobj(resp, f)

                        if extract:
                            print(f"Extracting to {local_path}...")
                            with gzip.open(gz_path, 'rb') as f_in:
                                with open(local_path, 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            gz_path.unlink()  # Delete .gz file

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
            print(f"HTTPS Error: {e}")
            return 0, []

    def _write_readme(self, downlist):
        readme_path = Path(self.savePath).parent / "README.txt"
        with open(readme_path, 'a') as f:
            f.write(f"\n{'='*10} Updated on: {datetime.date.today()} {'='*10}\n")
            f.write(f"HTTPS ADDRESS: {self.base_url}\n")
            f.write("DOWNLOADED FILES:\n")
            for remote, local in downlist:
                f.write(f"\t{remote}\tSAVED AS:\t{local}\n")
