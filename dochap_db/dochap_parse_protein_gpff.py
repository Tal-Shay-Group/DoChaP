"""
download_cdd_cache.py
Builds cdd_cache.json by combining two sources:

  1. NCBI CDD FTP — cddid.tbl.gz (~2MB)
     Authoritative list of ALL CDD entries: numeric PSSM-Id, accession,
     short name, description.

  2. EBI InterPro FTP — interpro.xml.gz (~39MB)
     Cross-references (Pfam, SMART, TIGR, InterPro accession).
     Only applied to CDD accessions that already exist in the NCBI table.

Usage:
    python download_cdd_cache.py [--out cdd_cache.json] [--keep-gz]
"""

import argparse
import gzip
import json
import re
import ssl
import sqlite3
import sys
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET



NCBI_CDDID_URL = "https://ftp.ncbi.nih.gov/pub/mmdb/cdd/cddid.tbl.gz"
EBI_INTERPRO_URL = "https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/interpro.xml.gz"

DB_MAP = {
    "PFAM":    "pfam",
    "SMART":   "smart",
    "TIGRFAM": "tigr",
    "NCBIFAM": "tigr",
}


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------



def download(url: str, dest: Path) -> None:
    print(f"Downloading {url}")
    context = ssl.create_default_context()
    with urllib.request.urlopen(url, context=context) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        block = 1024 * 64
        while chunk := resp.read(block):
            out.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = min(downloaded / total * 100, 100)
                print(f"\r  {pct:.1f}%  ({downloaded // 1024:,} KB / {total // 1024:,} KB)",
                      end="", flush=True)
            else:
                print(f"\r  {downloaded // 1024:,} KB", end="", flush=True)
    print()


# ---------------------------------------------------------------------------
# Step 1: parse NCBI cddid.tbl.gz
# ---------------------------------------------------------------------------

def parse_cddid(gz_path: Path) -> tuple[dict[int, dict], dict[str, dict]]:
    """Returns cache keyed by both lowercase accession AND numeric PSSM-Id string.
    Both keys point to the same dict object so enrichment via either key is reflected.
    """
    cdd_cache: dict[int, dict] = {}
    acc_cache: dict[str, dict] = {}

    with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            pssm_id, accession, short_name, description = parts[:4]
            cdd, pfam,smart,tigr,interpro = None, None,None,None,None
            acc_key = accession.lower()
            if acc_key.startswith("pfam") or acc_key.startswith("pf"):
               pfam = accession
            elif acc_key.startswith("smart") or acc_key.startswith("sm"):
               smart = accession
            elif acc_key.startswith("tigrt") or acc_key.startswith("ncbifam"):
               tigr = accession
            elif acc_key.startswith("cd"):
               cdd = accession

            record = {
                "cdd_id":      pssm_id,
                "name":        short_name.strip() or None,
                "other_name":  None,
                "description": description.strip() or None,
                "cdd":         cdd,
                "pfam":        pfam,
                "smart":       smart,
                "tigr":        tigr,
                "interpro":    None,
            }
            num_key = int(pssm_id.strip())
            if acc_key:
                acc_cache[acc_key] = record
            if num_key:
                cdd_cache[num_key] = record  # same object — enrichment writes once, visible via both keys

    return cdd_cache, acc_cache


# ---------------------------------------------------------------------------
# Step 2: enrich from interpro.xml.gz (only CDD accessions in cache)
# ---------------------------------------------------------------------------

def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def enrich_from_interpro(cache: dict[str, dict], gz_path: Path) -> int:
    """Stream-parse interpro.xml.gz and add pfam/smart/tigr/interpro to
    any record already present in cache. Returns number of enriched entries.
    """
    enriched = 0
    entry_count = 0

    with gzip.open(gz_path, "rb") as fh:
        context = ET.iterparse(fh, events=("end",))

        for event, elem in context:
            if elem.tag != "interpro":
                continue

            ipr_accession = elem.get("id")

            # Collect member db accessions
            members: dict[str, list[str]] = {}
            member_list = elem.find("member_list")
            if member_list is not None:
                for xref in member_list.findall("db_xref"):
                    db  = (xref.get("db") or "").upper()
                    key = (xref.get("dbkey") or "").strip()
                    if db and key:
                        members.setdefault(db, []).append(key)

            cdd_accessions = members.get("CDD", [])
            if not cdd_accessions:
                elem.clear()
                continue

            pfam  = ",".join(members.get("PFAM",    [])) or None
            smart = ",".join(members.get("SMART",   [])) or None
            tigr  = ",".join(
                members.get("TIGRFAM", []) + members.get("NCBIFAM", [])
            ) or None

            # Enrich only CDD entries that exist in the NCBI cache
            for cdd_acc in cdd_accessions:
                key = cdd_acc.lower()
                if key in cache:
                    record = cache[key]
                    record["pfam"]     = pfam
                    record["smart"]    = smart
                    record["tigr"]     = tigr
                    record["interpro"] = ipr_accession
                    enriched += 1
                                                                                                                                                                                                                          
            entry_count += 1
            if entry_count % 5000 == 0:
                print(f"  Parsed {entry_count:,} InterPro entries, {enriched} CDD entries enriched so far …")

            elem.clear()

    return enriched

def main():
    parser = argparse.ArgumentParser(
        description="Build CDD→InterPro cache from NCBI + EBI FTP files."
    )
    parser.add_argument("--out",     default="cdd_cache.json", help="Output JSON file (default: cdd_cache.json)")
    args = parser.parse_args()

    # --- NCBI cddid.tbl.gz ---
    cddid_gz = Path("cddid.tbl.gz")
    if not cddid_gz.exists():
        download(NCBI_CDDID_URL, cddid_gz)
    else:
        print(f"Found existing {cddid_gz} — skipping download.")

    print(f"Parsing {cddid_gz} …")
    cache = parse_cddid(cddid_gz)
    print(f"  {len(cache):,} keys loaded (accession + numeric PSSM-Id entries).")

    # --- EBI interpro.xml.gz ---
    interpro_gz = Path("interpro.xml.gz")
    if not interpro_gz.exists():
        download(EBI_INTERPRO_URL, interpro_gz)
    else:
        print(f"Found existing {interpro_gz} — skipping download.")

    print(f"Enriching from {interpro_gz} …")
    enriched = enrich_from_interpro(cache, interpro_gz)
    print(f"  {enriched} CDD entries enriched with Pfam/SMART/TIGR/InterPro cross-refs.")

    # Write output — deduplicate: only emit one record per unique dict object
    # (numeric keys and accession keys share the same object; avoid duplicates in output)
    seen: set[int] = set()
    output: dict[str, dict] = {}
    for key, record in cache.items():
        if id(record) not in seen:
            seen.add(id(record))
        output[key] = record  # keep both keys for lookup convenience

    with open(args.out, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(output):,} cache keys to {args.out}")



if __name__ == "__main__":
    main()
                          