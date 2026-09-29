#!/usr/bin/python
"""
List every input source of a DoChaP build - site, file and version - and store
the listing in DB_merged.sqlite as the table InputSources.

Versions are taken from the *downloaded files on disk*, never from the remote
sites: by the time this runs the site may already serve a newer release, while
the DB was built from whatever was downloaded. The evidence used, in order of
preference per source:

  1. headers inside the file itself
     - RefSeq  genomic.gff : '#!genome-build' / '#!genome-build-accession' /
                             '#!annotation-source'
     - Ensembl genomic.gff3: '#!genome-build' / '#!genebuild-last-updated'
     - InterPro *.xml.gz   : the <dbinfo dbname=".." version=".."/> records of
                             the <release> block that opens the file
  2. the README.txt blocks appended by ftpDownload/httpsDownload._write_readme,
     which record the address, the remote file name (the remote name carries
     the Ensembl release, e.g. Homo_sapiens.GRCh38.115.gff3) and the date
  3. the file name (e.g. ecod.v294.1.hierarchy.txt)

Sources that carry no version anywhere (BioMart TSVs, gene2ensembl, UniProt
idmapping) get version NULL - the download date in 'downloaded_on' is what
identifies them, and inventing a version for them would be worse than a NULL.

Run from the DoChaP-db directory, after downloading/building:

    python InputSourcesBuilder.py                  # write InputSources into DB_merged.sqlite
    python InputSourcesBuilder.py --dry-run        # only print the listing
    python InputSourcesBuilder.py --csv src.csv    # also dump to CSV
    python InputSourcesBuilder.py --db /path/DB_merged.sqlite --data-dir /path/data
"""
import argparse
import csv
import glob
import gzip
import hashlib
import os
import re
import sqlite3
import sys
from datetime import datetime
from itertools import islice

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_HERE)
sys.path.append(os.getcwd())
from conf import all_species, external  # noqa: E402

TABLE = "InputSources"

# Hosts the pipeline downloads from (see gffRefseqBuilder, gffEnsemblBuilder,
# IDconverterBuilder, DomainsEnsemblBuilder, OrthologsBuilder,
# InterproCollector and RepresentativeDomainsBuilder).
NCBI = "ftp.ncbi.nlm.nih.gov"
ENSEMBL = "ftp.ensembl.org"
EBI = "ftp.ebi.ac.uk"
BIOMART = "www.ensembl.org"
INTERPRO_API = "www.ebi.ac.uk"

COLUMNS = ("source", "dataset", "specie", "site", "remote_path", "file", "local_path",
           "version", "version_source", "file_date", "downloaded_on", "file_size",
           "n_files", "sha256", "status", "note", "recorded_on")


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _row(**kw):
    """A listing row with every column defaulted, so inserts stay positional-safe."""
    base = dict.fromkeys(COLUMNS)
    base.update(specie="all", status="missing", n_files=0)
    base.update(kw)
    return base


def _iso(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def _group_stat(paths):
    """(n_files, total size, newest mtime) over the files that actually exist."""
    present = [p for p in paths if os.path.isfile(p)]
    if not present:
        return 0, None, None
    size = sum(os.path.getsize(p) for p in present)
    mtime = max(os.path.getmtime(p) for p in present)
    return len(present), size, _iso(mtime)


def _sha256(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _rel(path, root):
    """Path relative to the build directory, for a readable local_path column."""
    try:
        return os.path.relpath(path, root)
    except ValueError:          # different drive / unrelated root
        return path


def _head(path, limit=200):
    """First `limit` lines of a plain or gzipped text file ([] if unreadable)."""
    opener = gzip.open if path.endswith(".gz") else open
    try:
        with opener(path, "rt", errors="replace") as fh:
            return list(islice(fh, limit))
    except (OSError, EOFError) as e:
        print("\t! could not read {}: {}".format(path, e))
        return []


# --------------------------------------------------------------------------- #
# version evidence
# --------------------------------------------------------------------------- #
_RE_README_DATE = re.compile(r"^=+\s*Updated on:\s*(\S+)\s*=+$")
_RE_README_ADDR = re.compile(r"^(?:HTTPS|FTP) ADDRESS:\s*(.+?)\s*$")
_RE_README_FILE = re.compile(r"^\t(.+?)\tSAVED AS:\t(.+?)\s*$")


def read_readme(path):
    """Parse a README.txt written by ftpDownload/httpsDownload._write_readme into
    {saved-as basename: {'remote':.., 'address':.., 'date':..}}.

    The downloaders *append* a block per run, so later blocks overwrite earlier
    ones here and the most recent download of each file wins - which is the one
    the DB was built from.
    """
    found = {}
    if not os.path.isfile(path):
        return found
    date = address = None
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            match = _RE_README_DATE.match(line.strip())
            if match:
                date = match.group(1)
                continue
            match = _RE_README_ADDR.match(line)
            if match:
                address = match.group(1)
                continue
            match = _RE_README_FILE.match(line)
            if match:
                remote, saved = match.group(1).strip(), match.group(2).strip()
                found[os.path.basename(saved)] = {"remote": remote, "address": address,
                                                  "date": date}
    return found


def split_address(address):
    """'https://ftp.ensembl.org/pub/current_gff3/homo_sapiens/' ->
       ('ftp.ensembl.org', '/pub/current_gff3/homo_sapiens')"""
    if not address:
        return None, None
    bare = re.sub(r"^[a-zA-Z]+://", "", address.strip())
    host, _, path = bare.partition("/")
    return host, ("/" + path.rstrip("/")) if path else "/"


def remote_gz_name(entry):
    """The README records the name *without* .gz, because both downloaders RETR/GET
    `remote_name + '.gz'`. Give back the real remote file name."""
    if not entry or not entry.get("remote"):
        return None
    remote = entry["remote"]
    return remote if remote.endswith(".gz") else remote + ".gz"


def gff_pragmas(path, limit=300):
    """The '#!key value' / '##key value' header lines of a gff/gff3 file."""
    pragmas = {}
    for line in _head(path, limit):
        if not line.startswith("#"):
            break
        match = re.match(r"^#[#!]\s*([\w.-]+)[ \t]+(.*)$", line.strip())
        if match:
            pragmas.setdefault(match.group(1), match.group(2).strip())
    return pragmas


_RE_DBINFO = re.compile(r"<dbinfo\b([^>]*?)/?>")
_RE_ATTR = re.compile(r'([\w-]+)="([^"]*)"')


def xml_dbinfo(path, limit=600):
    """{dbname: version} from the <release> block that opens InterPro's
    interpro.xml / match_complete.xml (the member-database versions come free
    with the InterPro version itself)."""
    versions = {}
    for line in _head(path, limit):
        for tag in _RE_DBINFO.findall(line):
            attrs = dict(_RE_ATTR.findall(tag))
            if attrs.get("dbname"):
                versions.setdefault(attrs["dbname"], attrs.get("version"))
        if "</release>" in line:
            break
    return versions


# --------------------------------------------------------------------------- #
# per-source collectors
# --------------------------------------------------------------------------- #
def collect_refseq(species, data_dir, root):
    """RefSeq genomic annotation + protein records (gffRefseqBuilder.downloader)."""
    rows = []
    save_path = os.path.join(data_dir, species, "refseq")
    # ftpDownload/httpsDownload write the README one level above savePath.
    readme = read_readme(os.path.join(data_dir, species, "README.txt"))

    # ---- genomic.gff -------------------------------------------------------
    gff = os.path.join(save_path, "genomic.gff")
    entry = readme.get("genomic.gff")
    site, remote_path = split_address(entry["address"]) if entry else (NCBI, None)
    n_files, size, mtime = _group_stat([gff])

    version = version_source = note = None
    if n_files:
        pragmas = gff_pragmas(gff)
        build = pragmas.get("genome-build")
        accession = (pragmas.get("genome-build-accession") or "").replace("NCBI_Assembly:", "")
        if build or accession:
            version = "{} ({})".format(build, accession) if build and accession else (build or accession)
            version_source = "genomic.gff header"
        note = "; ".join(filter(None, [
            "annotation-source: " + pragmas["annotation-source"] if "annotation-source" in pragmas else None,
            "annotation-date: " + pragmas["annotation-date"] if "annotation-date" in pragmas else None]))
    if not version and entry:
        # e.g. GCF_000001405.40_GRCh38.p14_genomic.gff
        match = re.match(r"(GCF_\d+\.\d+_.+?)_genomic", entry["remote"])
        if match:
            version, version_source = match.group(1), "README remote file name"
    rows.append(_row(
        source="RefSeq", dataset="genomic annotation (gff)", specie=species,
        site=site or NCBI, remote_path=remote_path, file=remote_gz_name(entry),
        local_path=_rel(gff, root), version=version, version_source=version_source,
        file_date=mtime, downloaded_on=entry["date"] if entry else None,
        file_size=size, n_files=n_files, status="present" if n_files else "missing",
        note=note or None))

    # ---- protein.gpff ------------------------------------------------------
    gpffs = sorted(glob.glob(os.path.join(save_path, "*protein.gpff")) +
                   glob.glob(os.path.join(save_path, "*protein.gpff.gz")))
    gpff_entries = [v for k, v in readme.items() if k.endswith("protein.gpff")]
    entry = gpff_entries[-1] if gpff_entries else None
    site, remote_path = split_address(entry["address"]) if entry else (NCBI, "/refseq/{}/mRNA_Prot".format(species))
    n_files, size, mtime = _group_stat(gpffs)
    rows.append(_row(
        source="RefSeq", dataset="protein records (gpff)", specie=species,
        site=site or NCBI, remote_path=remote_path,
        file=", ".join(sorted(os.path.basename(p) + ".gz" for p in gpffs)) or "*.protein.gpff.gz",
        local_path=_rel(save_path, root), version=None, version_source=None,
        file_date=mtime, downloaded_on=entry["date"] if entry else None,
        file_size=size, n_files=n_files, status="present" if n_files else "missing",
        note="mRNA_Prot flat files carry no release tag; identified by download date"))
    return rows


def collect_ensembl(species, data_dir, root):
    """Ensembl gff3 + the BioMart domain tables (gffEnsemblBuilder,
    DomainsEnsemblBuilder)."""
    rows = []
    save_path = os.path.join(data_dir, species, "ensembl")
    readme = read_readme(os.path.join(data_dir, species, "README.txt"))

    # ---- genomic.gff3 ------------------------------------------------------
    gff3 = os.path.join(save_path, "genomic.gff3")
    entry = readme.get("genomic.gff3")
    site, remote_path = split_address(entry["address"]) if entry else (ENSEMBL, "/pub/current_gff3")
    n_files, size, mtime = _group_stat([gff3])

    release = build = None
    note_bits = []
    if entry:
        # The release number survives only in the remote name - the file is saved
        # as genomic.gff3, and Ensembl gff3 headers do not carry the release.
        match = re.search(r"\.(\d+)\.gff3$", entry["remote"])
        release = match.group(1) if match else None
    if n_files:
        pragmas = gff_pragmas(gff3)
        build = pragmas.get("genome-build") or pragmas.get("genome-version")
        for key in ("genome-date", "genome-build-accession", "genebuild-last-updated"):
            if key in pragmas:
                note_bits.append("{}: {}".format(key, pragmas[key]))
    version = " / ".join(filter(None, ["release " + release if release else None, build])) or None
    version_source = " + ".join(filter(None, ["README remote file name" if release else None,
                                              "genomic.gff3 header" if build else None])) or None
    rows.append(_row(
        source="Ensembl", dataset="genomic annotation (gff3)", specie=species,
        site=site or ENSEMBL, remote_path=remote_path, file=remote_gz_name(entry),
        local_path=_rel(gff3, root), version=version, version_source=version_source,
        file_date=mtime, downloaded_on=entry["date"] if entry else None,
        file_size=size, n_files=n_files, status="present" if n_files else "missing",
        note="; ".join(note_bits) or None))

    # ---- BioMart domain tables --------------------------------------------
    biomart_dir = os.path.join(save_path, "BioMart")
    for ext_db in external:
        # mirrors DomainsEnsemblBuilder._expectedFiles
        if species == "R_norvegicus" and ext_db == "tigrfams":
            continue
        path = os.path.join(biomart_dir, "{}.Domains.{}.txt".format(species, ext_db))
        n_files, size, mtime = _group_stat([path])
        rows.append(_row(
            source="Ensembl BioMart", dataset="domains: " + ext_db, specie=species,
            site=BIOMART, remote_path="/biomart/martservice",
            file=os.path.basename(path), local_path=_rel(path, root),
            version=None, version_source=None, file_date=mtime, downloaded_on=None,
            file_size=size, n_files=n_files, status="present" if n_files else "missing",
            note="BioMart TSV carries no release tag; reflects the Ensembl release "
                 "that was current on the download date"))
    return rows


def collect_orthology(data_dir, root):
    """The per-pair BioMart orthology tables (OrthologsBuilder)."""
    rows = []
    download_path = os.path.join(data_dir, "orthology")
    for i in range(len(all_species)):
        for j in range(i, len(all_species)):
            if all_species[i] == all_species[j]:
                continue
            name = "{}.{}.orthology.txt".format(all_species[i], all_species[j])
            path = os.path.join(download_path, name)
            n_files, size, mtime = _group_stat([path])
            rows.append(_row(
                source="Ensembl BioMart", dataset="orthology",
                specie="{}-{}".format(all_species[i], all_species[j]),
                site=BIOMART, remote_path="/biomart/martservice", file=name,
                local_path=_rel(path, root), file_date=mtime, file_size=size,
                n_files=n_files, status="present" if n_files else "missing",
                note="BioMart TSV carries no release tag; reflects the Ensembl release "
                     "that was current on the download date"))
    return rows


def collect_ncbi_gene(data_dir, root, build_dir):
    """gene2ensembl, the RefSeq<->Ensembl id map (IDconverterBuilder)."""
    # IDconverterBuilder saves into data/, so its README lands in the build dir.
    readme = read_readme(os.path.join(build_dir, "README.txt"))
    entry = readme.get("gene2ensembl.txt")
    site, remote_path = split_address(entry["address"]) if entry else (NCBI, "/gene/DATA")
    path = os.path.join(data_dir, "gene2ensembl.txt")
    n_files, size, mtime = _group_stat([path])
    return [_row(
        source="NCBI Gene", dataset="RefSeq<->Ensembl id mapping", specie="all",
        site=site or NCBI, remote_path=remote_path,
        file=remote_gz_name(entry) or "gene2ensembl.gz", local_path=_rel(path, root),
        file_date=mtime, downloaded_on=entry["date"] if entry else None,
        file_size=size, n_files=n_files, status="present" if n_files else "missing",
        note="gene2ensembl carries no release tag; identified by download date")]


def collect_interpro(data_dir, root, build_dir):
    """InterPro matches + curated entries (RepresentativeDomainsBuilder,
    InterproCollector)."""
    rows = []
    readme = read_readme(os.path.join(build_dir, "README.txt"))

    for local_name, dataset in (("match_complete.xml.gz", "protein domain matches"),
                                ("interpro.xml.gz", "curated entry metadata")):
        path = os.path.join(data_dir, local_name)
        entry = readme.get(local_name[:-3])          # README records the un-gzipped name
        site, remote_path = split_address(entry["address"]) if entry else \
            (EBI, "/pub/databases/interpro/current_release")
        n_files, size, mtime = _group_stat([path])
        version = version_source = note = None
        if n_files:
            versions = xml_dbinfo(path)
            version = versions.pop("INTERPRO", None)
            if version:
                version_source = "<dbinfo> of the <release> block"
            members = ", ".join("{} {}".format(k, v) for k, v in sorted(versions.items()) if v)
            note = "member DBs: " + members if members else None
        rows.append(_row(
            source="InterPro", dataset=dataset, specie="all",
            site=site or EBI, remote_path=remote_path, file=local_name,
            local_path=_rel(path, root), version=version, version_source=version_source,
            file_date=mtime, downloaded_on=entry["date"] if entry else None,
            file_size=size, n_files=n_files, status="present" if n_files else "missing",
            note=note))

    # InterPro REST dump (InterproCollector) - a paged API crawl, no release tag.
    path = os.path.join(data_dir, "InterPro_entries.txt")
    n_files, size, mtime = _group_stat([path])
    rows.append(_row(
        source="InterPro", dataset="entry list (REST API)", specie="all",
        site=INTERPRO_API, remote_path="/interpro/api/entry/InterPro/",
        file="InterPro_entries.txt", local_path=_rel(path, root),
        file_date=mtime, file_size=size, n_files=n_files,
        status="present" if n_files else "missing",
        note="API crawl carries no release tag; identified by download date"))
    return rows


def collect_uniprot(data_dir, root, build_dir):
    """UniProt idmapping_selected (RepresentativeDomainsBuilder)."""
    readme = read_readme(os.path.join(build_dir, "README.txt"))
    entry = readme.get("idmapping_selected.tab")
    site, remote_path = split_address(entry["address"]) if entry else \
        (EBI, "/pub/databases/uniprot/current_release/knowledgebase/idmapping")
    path = os.path.join(data_dir, "idmapping_selected.tab.gz")
    n_files, size, mtime = _group_stat([path])
    return [_row(
        source="UniProt", dataset="id mapping", specie="all",
        site=site or EBI, remote_path=remote_path, file="idmapping_selected.tab.gz",
        local_path=_rel(path, root), file_date=mtime,
        downloaded_on=entry["date"] if entry else None, file_size=size, n_files=n_files,
        status="present" if n_files else "missing",
        note="idmapping_selected carries no release tag; identified by download date")]


# --------------------------------------------------------------------------- #
# extra (enrichment) sources: listed only when actually present on disk
# --------------------------------------------------------------------------- #
# dir under data/ -> (source label, site, remote path)
EXTRA_DIRS = {
    "pfam":          ("Pfam", EBI, "/pub/databases/Pfam/current_release"),
    "afdb":          ("AlphaFold DB", EBI, "/pub/databases/alphafold/latest"),
    "uniprot":       ("UniProt", "ftp.uniprot.org",
                      "/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes"),
    "alphamissense": ("AlphaMissense", "zenodo.org", "/records/8208688/files"),
    "appris":        ("APPRIS", "apprisws.bioinfo.cnio.es", "/pub/current_release"),
    "gnomad":        ("gnomAD", "storage.googleapis.com",
                      "/gcp-public-data--gnomad/release/2.1.1/constraint"),
}
# Derived artefacts and index files - not downloaded inputs, so never listed.
EXTRA_SKIP_SUFFIXES = (".sqlite", ".sqlite3", ".db", ".part",
                       ".h3i", ".h3f", ".h3m", ".h3p")


def version_from_name(name):
    """Version embedded in a file name: ecod.v294.1.hierarchy.txt -> 'v294.1',
    UP000005640_9606_HUMAN_v4.tar -> 'v4', gnomad.v2.1.1... -> 'v2.1.1'."""
    match = re.search(r"[._]v(\d+(?:\.\d+)*)\b", name)
    return "v" + match.group(1) if match else None


def collect_extra(data_dir, root):
    """Enrichment inputs (Pfam/AlphaFold/ECOD/...) that sit next to the DoChaP
    downloads. Only files that exist are listed, so a plain DoChaP build simply
    produces no rows here."""
    rows = []
    for sub, (source, site, remote_path) in sorted(EXTRA_DIRS.items()):
        directory = os.path.join(data_dir, sub)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name)
            if not os.path.isfile(path) or name.endswith(EXTRA_SKIP_SUFFIXES):
                continue
            n_files, size, mtime = _group_stat([path])
            version = version_from_name(name)
            rows.append(_row(
                source=source, dataset="enrichment input", specie="all", site=site,
                remote_path=remote_path, file=name, local_path=_rel(path, root),
                version=version, version_source="file name" if version else None,
                file_date=mtime, file_size=size, n_files=n_files, status="present"))

    # ECOD ships as loose files in data/ rather than its own directory.
    for path in sorted(glob.glob(os.path.join(data_dir, "ecod.*"))):
        if not os.path.isfile(path) or path.endswith(EXTRA_SKIP_SUFFIXES):
            continue
        name = os.path.basename(path)
        version = version_from_name(name)
        if not version:
            # ECOD text files open with a comment naming the build, e.g.
            # '#/data/ecod/database_versions/v294/ecod.develop294'
            head = "".join(_head(path, 3))
            match = re.search(r"ecod\.develop(\d+)", head) or re.search(r"/v(\d+(?:\.\d+)*)/", head)
            version = "v" + match.group(1) if match else None
        n_files, size, mtime = _group_stat([path])
        rows.append(_row(
            source="ECOD", dataset="enrichment input", specie="all",
            site="prodata.swmed.edu", remote_path="/ecod/distributions", file=name,
            local_path=_rel(path, root), version=version,
            version_source="file name" if version else None,
            file_date=mtime, file_size=size, n_files=n_files, status="present"))
    return rows


def collect_all(data_dir, build_dir, root, with_extra=True):
    rows = []
    for species in all_species:
        rows += collect_refseq(species, data_dir, root)
        rows += collect_ensembl(species, data_dir, root)
    rows += collect_orthology(data_dir, root)
    rows += collect_ncbi_gene(data_dir, root, build_dir)
    rows += collect_interpro(data_dir, root, build_dir)
    rows += collect_uniprot(data_dir, root, build_dir)
    if with_extra:
        rows += collect_extra(data_dir, root)
    return rows


# --------------------------------------------------------------------------- #
# output
# --------------------------------------------------------------------------- #
def write_table(db_path, rows, append=False):
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        if not append:
            cur.execute("DROP TABLE IF EXISTS {};".format(TABLE))
        cur.execute("""
            CREATE TABLE IF NOT EXISTS {}(
                    source TEXT,
                    dataset TEXT,
                    specie TEXT,
                    site TEXT,
                    remote_path TEXT,
                    file TEXT,
                    local_path TEXT,
                    version TEXT,
                    version_source TEXT,
                    file_date TEXT,
                    downloaded_on TEXT,
                    file_size INTEGER,
                    n_files INTEGER,
                    sha256 TEXT,
                    status TEXT,
                    note TEXT,
                    recorded_on TEXT
                    );""".format(TABLE))
        cur.executemany(
            "INSERT INTO {}({}) VALUES({});".format(
                TABLE, ", ".join(COLUMNS), ", ".join("?" * len(COLUMNS))),
            [tuple(row[c] for c in COLUMNS) for row in rows])
        con.commit()


def write_csv(csv_path, rows):
    with open(csv_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def print_rows(rows):
    header = ("SOURCE", "SPECIE", "DATASET", "SITE", "FILE", "VERSION", "STATUS")
    table = [header] + [(r["source"] or "", r["specie"] or "", r["dataset"] or "",
                         r["site"] or "", (r["file"] or "")[:42], r["version"] or "-",
                         r["status"]) for r in rows]
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]
    for i, row in enumerate(table):
        print("  ".join(cell.ljust(widths[j]) for j, cell in enumerate(row)).rstrip())
        if i == 0:
            print("  ".join("-" * w for w in widths))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default="DB_merged.sqlite",
                        help="database to write the {} table into (default: %(default)s)".format(TABLE))
    parser.add_argument("--data-dir", default=None,
                        help="the downloads directory (default: <build dir>/data)")
    parser.add_argument("--build-dir", default=os.getcwd(),
                        help="directory the pipeline was run from, where the top-level "
                             "README.txt is written (default: cwd)")
    parser.add_argument("--append", action="store_true",
                        help="keep previous rows instead of replacing the table")
    parser.add_argument("--hash", action="store_true",
                        help="also record a sha256 per file (slow on the big files)")
    parser.add_argument("--no-extra", action="store_true",
                        help="skip the enrichment inputs (Pfam/AlphaFold/ECOD/...)")
    parser.add_argument("--csv", default=None, help="also write the listing to this CSV")
    parser.add_argument("--dry-run", action="store_true", help="print only, do not touch the DB")
    args = parser.parse_args(argv)

    build_dir = os.path.abspath(args.build_dir)
    data_dir = os.path.abspath(args.data_dir) if args.data_dir else os.path.join(build_dir, "data")
    if not os.path.isdir(data_dir):
        sys.exit("No downloads directory at {} - run this from the DoChaP-db directory "
                 "or pass --data-dir".format(data_dir))

    print("Collecting input sources from {}".format(data_dir))
    rows = collect_all(data_dir, build_dir, build_dir, with_extra=not args.no_extra)

    if args.hash:
        for row in rows:
            path = os.path.join(build_dir, row["local_path"] or "")
            if row["status"] == "present" and row["n_files"] == 1 and os.path.isfile(path):
                row["sha256"] = _sha256(path)

    recorded_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for row in rows:
        row["recorded_on"] = recorded_on

    print_rows(rows)
    missing = [r for r in rows if r["status"] == "missing"]
    print("\n{} sources listed, {} present, {} missing".format(
        len(rows), len(rows) - len(missing), len(missing)))
    if missing:
        print("missing (never downloaded, or downloaded elsewhere):")
        for row in missing:
            print("\t{} / {} / {}".format(row["source"], row["specie"], row["dataset"]))

    if args.csv:
        write_csv(args.csv, rows)
        print("wrote {}".format(args.csv))

    if args.dry_run:
        print("--dry-run: {} not written".format(TABLE))
        return 0

    if not os.path.exists(args.db):
        print("! {} does not exist yet - it will be created with only the {} table".format(
            args.db, TABLE))
    write_table(args.db, rows, append=args.append)
    print("{} rows {} {} in {}".format(len(rows), "appended to" if args.append else "written to",
                                       TABLE, args.db))
    return 0


if __name__ == "__main__":
    sys.exit(main())
