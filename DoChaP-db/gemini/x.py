from ftplib import FTP

ftp = FTP("ftp.ncbi.nlm.nih.gov")
try:
    ftp.login(user='anonymous', passwd='example@post.bgu.ac.il')                # 1. Authenticate first
    ftp.set_pasv(True)         # 2. THEN enable passive mode
    # Now you can safely call nlst()
    folders = ftp.nlst("/genomes/all/GCF/000/001/405")
    print(folders)
except Exception as e:
    print(f'Failed due to {e}');
ftp.close()
