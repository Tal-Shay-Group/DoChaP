# One UniProt accession maps to one transcript, so canonicals lose their domains

Found while checking why DOMAS reported `added_domain` for PTPRC/CD45 against a
canonical that DoChaP itself shows domains for. The analysis-side consequence is
written up in `domas_extra/CELLTYPE_ANALYSIS.md`; this file is about the build.

Two separate defects, one cause. Same shape as the `syno[0]` bug in
`gffRefseqBuilder.py:305` - a multi-valued source field read as if it held one
value.

## What is wrong

`Proteins.protein_interpro_id` is populated by
`RepresentativeDomainsBuilder.populate_dochap_protein_mapping()` from UniProt's
`idmapping_selected.tab.gz`. Both source columns it reads are **`"; "`-separated
lists** when an accession maps to several identifiers:

```
col 3   RefSeq         "NP_002829.3; NP_563578.2"
col 19  Ensembl_TRS    "ENST00000348564.12; ENST00000442510.8; ENST00000367379.6"
```

Neither is split.

**The RefSeq branch** compares the whole field against a single id:

```python
if refseq_id and refseq_id in refseq_to_pair:
```

`"NP_002829.3; NP_563578.2"` is not a key in `refseq_to_pair`, so a multi-valued
line matches nothing at all on this branch.

**The Ensembl branch** is worse, because it silently half-works:

```python
enst_bare = enst_id.split('.')[0]
for key in (enst_id, enst_bare):
    if key in transcript_ensembl_to_pair:
        ensembl_hits[transcript_ensembl_to_pair[key]] = uniprot_acc
        break
```

`.split('.')[0]` on the list above yields `ENST00000348564` - the *first*
transcript, bare - because the first `.` it meets is that id's version dot. The
`break` then stops after one hit. So each mapping line can claim **exactly one
transcript**, and every other transcript sharing that accession is dropped
without a warning.

## The signature in the finished database

If each line claims one transcript, accessions should be almost perfectly 1:1
with transcripts. They are:

```
transcripts per accession      accessions
        1                        333,938
        2                          1,466
        3+                             0
```

333,938 of 335,404 (99.6%) map to a single transcript. Biologically an accession
covers a gene product with many isoforms, so this distribution is a build
artefact, not the data.

Coverage overall:

```
Proteins rows ................ 730,522
  with an accession .......... 336,870   (46.1%)
  with none .................. 393,652   (53.9%)

canonical transcripts with a protein ... 117,931
  with no accession ....................  36,529   (31.0%)
     ...whose gene HAS one on some other transcript ... 13,530
```

**Nearly a third of canonical transcripts carry no accession**, and for 13,530 of
them the gene's accession exists - it just landed on a different transcript.

Reviewed entries are the ones that lose, because they are exactly the ones
listing many isoforms; TrEMBL `A0A*` entries are usually isoform-specific and so
map 1:1 and survive:

```
accessions present:  208,454 TrEMBL A0A*   128,416 other (largely reviewed)

genes with a reviewed-style accession somewhere ....... 63,913
  the canonical carries it ............................ 52,268  (81.8%)
  it sits on a NON-canonical transcript ............... 11,645  (18.2%)
```

## Confirmed against the source file (2026-08-19)

The diagnosis below was originally derived from the builder source and the
finished database. `idmapping_selected.tab.gz` (UniProt **2026_02**,
7,066,467,385 bytes) has since been downloaded and the PTPRC line read directly.
It contains **exactly one** record mentioning any PTPRC identifier:

```
UniProtKB-AC  P08575
RefSeq        NP_002829.3; NP_563578.2; XP_006711535.1; ... (16 entries)
Ensembl       ENSG00000081237.23; ENSG00000262418.5
Ensembl_TRS   ENST00000348564.12; ENST00000442510.8; ENST00000573477.5; ... (9 entries)
Ensembl_PRO   ENSP00000306782.7; ENSP00000411355.3; ... (9 entries)
```

Both the canonical transcript (`ENST00000442510.8`) and its RefSeq protein
(`NP_002829.3`) are present. Neither is reached:

- **RefSeq branch** compares the whole field against one key.
  `"NP_002829.3; NP_563578.2; ..."` is not `"NP_002829.3"`, so a 16-entry field
  matches nothing - even though the canonical's protein is listed **first**.
- **Ensembl branch** computes `enst_id.split('.')[0]` = `ENST00000348564` - the
  first transcript, bare - matches it, and `break`s. `ENST00000442510.8` is
  listed **second** and is never examined.

Nine transcripts share `P08575`; the builder assigns it to one.

**The two defects in this file are one bug.** `P08575`'s domain coordinates run
to residue 1,302, and:

```
ENST00000442510.8  (canonical)  1,306 aa   1302 <= 1306   FITS
ENST00000348564.12             1,145 aa   1302 >  1145   does NOT fit
```

The accession describes the full-length CD45 protein, which is the **canonical**.
It was attached to a shorter transcript solely because that transcript is listed
first, which is also why the coordinates overflow it. Correcting the attachment
fixes the overflow.

## PTPRC, the case that surfaced it

```
ENST00000442510.8   NM_002838.5   1,306 aa   canonical   accession: (none)
ENST00000348564.12  NM_080921.4   1,145 aa               accession: P08575
```

`P08575` is the reviewed Swiss-Prot entry for CD45 and carries five
`RepresentativeDomains` rows (IPR016335, IPR003961 x2, IPR029021 x2). It reached
a shorter, non-canonical transcript; the canonical got nothing, so anything
reading domains through `protein_interpro_id` sees the canonical CD45 as having
no domains whatsoever - while `SpliceInDomains` holds 65 rows for it and the
DoChaP web view draws them.

Of PTPRC's 20 protein rows, 14 carry an accession - all the fragment isoforms
with their own TrEMBL ids. The full-length canonical is one of the 6 without.

## Second defect: coordinates attached to the wrong isoform

Where an accession does land on a transcript, it brings the domain coordinates
of the accession's own sequence, which need not be that transcript's:

```
P08575  ->  ENST00000348564.12,  Proteins.length = 1,145
            RepresentativeDomains max end = 1,302      (157 residues past the end)
```

Across the database:

```
proteins with domains ............ 257,790
  max domain end > protein length .. 20,454   (7.9%)
```

So 7.9% of annotated proteins carry at least one domain that cannot fit in them.
Any consumer that projects these coordinates onto exons is reading past the
sequence.

## What to do

1. **Split both fields.** `field.split('; ')` on columns 3 and 19, and record
   every id, not the first. Confirmed necessary: PTPRC's record carries 16 RefSeq
   and 9 Ensembl_TRS entries in single cells. Removing the `break` is part of it - the loop over
   `(enst_id, enst_bare)` is a versioned/bare fallback for one id and must not
   double as "stop at the first transcript".
2. **Stop using `.split('.')[0]` on a possibly multi-valued field.** It cannot
   fail loudly: it always returns something that looks like a bare id.
3. **Decide what a shared accession means** before fixing 1. `refseq_hits` and
   `ensembl_hits` are keyed by protein pair and last-write-wins, so once one line
   legitimately claims several transcripts, the existing collision handling
   (`COLLISION_STRATEGIES`) starts firing on cases it was not written for.
4. **Guard the coordinates.** A domain whose `end` exceeds `Proteins.length` for
   the transcript it is attached to should be rejected or flagged at build time,
   not carried.
5. Re-check the 7.9% overflow after 1-3: some of it should disappear once
   accessions reach the isoform they actually describe.

A rebuild is required for any of this. The source files needed are
`idmapping_selected.tab.gz` (UniProt 2026_02, 6.6 GB),
`match_complete.xml.gz` (InterPro 109.0, 52 GB) and `interpro.xml.gz` (40 MB);
none is kept on disk after a build. The diagnosis above has been verified against
a fresh `idmapping_selected.tab.gz` - see the confirmation section.
