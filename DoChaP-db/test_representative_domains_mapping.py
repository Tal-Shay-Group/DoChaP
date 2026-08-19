"""Regression test for the idmapping multi-value bug.

UNIPROT_MAPPING_LOSES_CANONICALS.md: columns 3 and 19 of idmapping_selected.tab
are "; "-separated lists. Reading either as a single value silently dropped every
id but the first, which left 31% of canonical transcripts with no accession and
therefore no domains at all.

PTPRC is the case that surfaced it: one line, accession P08575, listing 16 RefSeq
proteins and 9 Ensembl transcripts. The canonical ENST00000442510.8 is SECOND in
that list, so the old code never reached it.

Run: python3 test_representative_domains_mapping.py
"""
import gzip, os, sqlite3, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from RepresentativeDomainsBuilder import (populate_dochap_protein_mapping,
                                          _split_ids, _claim)

REFSEQ = ("NP_002829.3; NP_563578.2; XP_006711535.1; XP_006711536.1; "
          "XP_006711537.1; XP_047282337.1; XP_047282354.1")
ENSTS = ("ENST00000348564.12; ENST00000442510.8; ENST00000573477.5; "
         "ENST00000573679.5; ENST00000697631.1; ENST00000908298.1; "
         "ENST00000970623.1; ENST00000970624.1; ENST00000970626.1")
# ENST00000573477 / ENST00000573679 are not in DoChaP, so 7 of the 9 can map.
IN_DOCHAP = ["ENST00000348564.12", "ENST00000442510.8", "ENST00000697631.1",
             "ENST00000908298.1", "ENST00000970623.1", "ENST00000970624.1",
             "ENST00000970626.1"]


def _line(acc, uid, refseq, ensts):
    f = [''] * 22
    f[0], f[1], f[3], f[19] = acc, uid, refseq, ensts
    return '\t'.join(f)


def test_split_ids():
    assert _split_ids("NP_002829.3; NP_563578.2") == ("NP_002829.3", "NP_563578.2")
    assert _split_ids("") == ()
    assert _split_ids("ENST1.1") == ("ENST1.1",)


def test_reviewed_preference():
    h = {}
    _claim(h, ('p', 'e'), 'A0ATREMBL', False)
    _claim(h, ('p', 'e'), 'P08575', True)
    assert h[('p', 'e')] == ('P08575', True), "reviewed must displace unreviewed"
    _claim(h, ('p', 'e'), 'A0AOTHER', False)
    assert h[('p', 'e')] == ('P08575', True), "unreviewed must not displace reviewed"
    h2 = {}
    _claim(h2, ('p', 'e'), 'P08575', True)
    _claim(h2, ('p', 'e'), 'A0ATREMBL', False)
    assert h2[('p', 'e')] == ('P08575', True), "order must not matter"


def test_every_listed_transcript_is_mapped():
    con = sqlite3.connect(':memory:')
    cur = con.cursor()
    cur.execute("""CREATE TABLE Proteins(protein_refseq_id TEXT, protein_ensembl_id TEXT,
                                         transcript_ensembl_id TEXT, protein_interpro_id TEXT)""")
    cur.executemany("INSERT INTO Proteins VALUES (?,?,?,NULL)",
                    [(f"NP_{i}", f"ENSP_{i}", t) for i, t in enumerate(IN_DOCHAP)])

    tmp = tempfile.NamedTemporaryFile(suffix='.tab.gz', delete=False)
    try:
        with gzip.open(tmp.name, 'wt') as fh:
            fh.write(_line('P08575', 'PTPRC_HUMAN', REFSEQ, ENSTS) + '\n')
            # written AFTER the reviewed entry: under last-write-wins this would
            # steal the canonical.
            fh.write(_line('A0ATEST999', 'A0ATEST999_HUMAN', '', 'ENST00000442510.8') + '\n')
        populate_dochap_protein_mapping(cur, tmp.name)
    finally:
        os.unlink(tmp.name)

    got = dict(cur.execute("SELECT transcript_ensembl_id, protein_interpro_id "
                           "FROM Proteins WHERE protein_interpro_id IS NOT NULL"))
    assert got.get('ENST00000442510.8') == 'P08575', \
        f"canonical must get the reviewed accession, got {got.get('ENST00000442510.8')!r}"
    missing = [t for t in IN_DOCHAP if t not in got]
    assert not missing, f"one line must map every listed transcript; missed {missing}"
    assert len(set(got.values())) == 1, f"all should share P08575, got {set(got.values())}"


if __name__ == '__main__':
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith('test_')):
        fn(); print(f"PASS  {name}")
    print("\nall tests passed")
