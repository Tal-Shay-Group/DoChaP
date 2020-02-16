/* this controller for the result page should handle different view options and previwing the 
graphics properly when the page loads. It should also allow tooltips of kinds and windows if needed. */
angular.module("DoChaP")
    .controller("resultsController", function ($scope, $window, $route) {
        self = this;
        $scope.loadingText = false;
        var loadedGene = JSON.parse($window.sessionStorage.getItem("currGene"));
        var ignorePredictions = JSON.parse($window.sessionStorage.getItem("ignorePredictions"));
        isReviewedCheckBox.checked = ignorePredictions;
        $scope.canvasSize = 550;
        $scope.viewMode = "all";
        self.toolTipManagerForCanvas = {
            "canvas-protein0": [
                [50, 0, 50, 70, " this is red"],
                [150, 0, 50, 70, "this is blue"]
            ]
        };
        if (loadedGene == undefined) {
            //example in case nothing is entered in search
            loadedGene = {
                "genes": [{
                    "gene_id": "99650",
                    "gene_symbol": "4933434E20Rik",
                    "synonyms": "5730552F22Rik; AI462154; NICE-3; NS5ATP4",
                    "chromosome": "chr3",
                    "strand": "+",
                    "MGI_id": "1914027",
                    "ensembl_id": "ENSMUSG00000027942",
                    "description": null,
                    "specie": "M_musculus",
                    "transcripts": [{
                        "transcript_id": "NM_001287087.1",
                        "tx_start": 90051635,
                        "tx_end": 90063341,
                        "cds_start": 90053053,
                        "cds_end": 90061833,
                        "gene_id": "99650",
                        "exon_count": 9,
                        "ensembl_ID": "ENSMUST00000159064.7",
                        "ucsc_id": "uc008qbd.4",
                        "protein_id": "NP_001274016.1",
                        "transcriptExons": [{
                            "transcript_id": "NM_001287087.1",
                            "order_in_transcript": 1,
                            "genomic_start_tx": 90051635,
                            "genomic_end_tx": 90051693,
                            "abs_start_CDS": 0,
                            "abs_end_CDS": 0
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "order_in_transcript": 2,
                            "genomic_start_tx": 90052600,
                            "genomic_end_tx": 90052785,
                            "abs_start_CDS": 0,
                            "abs_end_CDS": 0
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "order_in_transcript": 3,
                            "genomic_start_tx": 90052899,
                            "genomic_end_tx": 90053119,
                            "abs_start_CDS": 1,
                            "abs_end_CDS": 66
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "order_in_transcript": 4,
                            "genomic_start_tx": 90053507,
                            "genomic_end_tx": 90053609,
                            "abs_start_CDS": 67,
                            "abs_end_CDS": 168
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "order_in_transcript": 5,
                            "genomic_start_tx": 90056206,
                            "genomic_end_tx": 90056324,
                            "abs_start_CDS": 169,
                            "abs_end_CDS": 286
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "order_in_transcript": 6,
                            "genomic_start_tx": 90056528,
                            "genomic_end_tx": 90056582,
                            "abs_start_CDS": 287,
                            "abs_end_CDS": 340
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "order_in_transcript": 7,
                            "genomic_start_tx": 90058484,
                            "genomic_end_tx": 90058651,
                            "abs_start_CDS": 341,
                            "abs_end_CDS": 507
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "order_in_transcript": 8,
                            "genomic_start_tx": 90058741,
                            "genomic_end_tx": 90058800,
                            "abs_start_CDS": 508,
                            "abs_end_CDS": 566
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "order_in_transcript": 9,
                            "genomic_start_tx": 90061637,
                            "genomic_end_tx": 90063341,
                            "abs_start_CDS": 567,
                            "abs_end_CDS": 762
                        }],
                        "protein": {
                            "protein_id": "NP_001274016.1",
                            "description": "uncharacterized protein C1orf43 homolog isoform 1 [Mus musculus]",
                            "synonyms": "uncharacterized protein C1orf43 homolog",
                            "length": 253,
                            "ensembl_id": "ENSMUSP00000124554.1",
                            "uniprot_id": "Q8R092",
                            "gene_id": "99650",
                            "transcript_id": "NM_001287087.1"
                        },
                        "domains": [{
                            "protein_id": "NP_001274016.1",
                            "type_id": 23438,
                            "AA_start": 6,
                            "AA_end": 188,
                            "nuc_start": 16,
                            "nuc_end": 564,
                            "total_length": 549,
                            "splice_junction": 1,
                            "complete_exon": 0,
                            "domainType": {
                                "type_id": 23438,
                                "name": "NICE-3",
                                "description": "NICE-3 protein; ",
                                "external_id": "pfam07406",
                                "CDD_id": 284755
                            }
                        }],
                        "spliceInDomains": [{
                            "transcript_id": "NM_001287087.1",
                            "exon_order_in_transcript": 3,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": -51,
                            "exon_num_in_domain": 1
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "exon_order_in_transcript": 4,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 102,
                            "exon_num_in_domain": 2
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "exon_order_in_transcript": 5,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 118,
                            "exon_num_in_domain": 3
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "exon_order_in_transcript": 6,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 54,
                            "exon_num_in_domain": 4
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "exon_order_in_transcript": 7,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 167,
                            "exon_num_in_domain": 5
                        }, {
                            "transcript_id": "NM_001287087.1",
                            "exon_order_in_transcript": 8,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 57,
                            "exon_num_in_domain": 6
                        }]
                    }, {
                        "transcript_id": "NM_027500.4",
                        "tx_start": 90052801,
                        "tx_end": 90058867,
                        "cds_start": 90053053,
                        "cds_end": 90058804,
                        "gene_id": "99650",
                        "exon_count": 6,
                        "ensembl_ID": "ENSMUST00000029552.12",
                        "ucsc_id": "uc008qba.4",
                        "protein_id": "NP_081776.2",
                        "transcriptExons": [{
                            "transcript_id": "NM_027500.4",
                            "order_in_transcript": 1,
                            "genomic_start_tx": 90052801,
                            "genomic_end_tx": 90053119,
                            "abs_start_CDS": 1,
                            "abs_end_CDS": 66
                        }, {
                            "transcript_id": "NM_027500.4",
                            "order_in_transcript": 2,
                            "genomic_start_tx": 90053507,
                            "genomic_end_tx": 90053609,
                            "abs_start_CDS": 67,
                            "abs_end_CDS": 168
                        }, {
                            "transcript_id": "NM_027500.4",
                            "order_in_transcript": 3,
                            "genomic_start_tx": 90056206,
                            "genomic_end_tx": 90056324,
                            "abs_start_CDS": 169,
                            "abs_end_CDS": 286
                        }, {
                            "transcript_id": "NM_027500.4",
                            "order_in_transcript": 4,
                            "genomic_start_tx": 90056528,
                            "genomic_end_tx": 90056582,
                            "abs_start_CDS": 287,
                            "abs_end_CDS": 340
                        }, {
                            "transcript_id": "NM_027500.4",
                            "order_in_transcript": 5,
                            "genomic_start_tx": 90058484,
                            "genomic_end_tx": 90058651,
                            "abs_start_CDS": 341,
                            "abs_end_CDS": 507
                        }, {
                            "transcript_id": "NM_027500.4",
                            "order_in_transcript": 6,
                            "genomic_start_tx": 90058741,
                            "genomic_end_tx": 90058867,
                            "abs_start_CDS": 508,
                            "abs_end_CDS": 570
                        }],
                        "protein": {
                            "protein_id": "NP_081776.2",
                            "description": "uncharacterized protein C1orf43 homolog isoform 2 [Mus musculus]",
                            "synonyms": "uncharacterized protein C1orf43 homolog",
                            "length": 189,
                            "ensembl_id": "ENSMUSP00000029552.6",
                            "uniprot_id": "Q8R092",
                            "gene_id": "99650",
                            "transcript_id": "NM_027500.4"
                        },
                        "domains": [{
                            "protein_id": "NP_081776.2",
                            "type_id": 23439,
                            "AA_start": 6,
                            "AA_end": 188,
                            "nuc_start": 16,
                            "nuc_end": 564,
                            "total_length": 549,
                            "splice_junction": 1,
                            "complete_exon": 0,
                            "domainType": {
                                "type_id": 23439,
                                "name": "NICE-3",
                                "description": "NICE-3 protein; ",
                                "external_id": "pfam07406",
                                "CDD_id": 311382
                            }
                        }],
                        "spliceInDomains": [{
                            "transcript_id": "NM_027500.4",
                            "exon_order_in_transcript": 1,
                            "type_id": 23439,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": -51,
                            "exon_num_in_domain": 1
                        }, {
                            "transcript_id": "NM_027500.4",
                            "exon_order_in_transcript": 2,
                            "type_id": 23439,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 102,
                            "exon_num_in_domain": 2
                        }, {
                            "transcript_id": "NM_027500.4",
                            "exon_order_in_transcript": 3,
                            "type_id": 23439,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 118,
                            "exon_num_in_domain": 3
                        }, {
                            "transcript_id": "NM_027500.4",
                            "exon_order_in_transcript": 4,
                            "type_id": 23439,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 54,
                            "exon_num_in_domain": 4
                        }, {
                            "transcript_id": "NM_027500.4",
                            "exon_order_in_transcript": 5,
                            "type_id": 23439,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 167,
                            "exon_num_in_domain": 5
                        }, {
                            "transcript_id": "NM_027500.4",
                            "exon_order_in_transcript": 6,
                            "type_id": 23439,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 57,
                            "exon_num_in_domain": 6
                        }]
                    }, {
                        "transcript_id": "NM_001287086.1",
                        "tx_start": 90052801,
                        "tx_end": 90063341,
                        "cds_start": 90058525,
                        "cds_end": 90061833,
                        "gene_id": "99650",
                        "exon_count": 5,
                        "ensembl_ID": "",
                        "ucsc_id": "",
                        "protein_id": "NP_001274015.1",
                        "transcriptExons": [{
                            "transcript_id": "NM_001287086.1",
                            "order_in_transcript": 1,
                            "genomic_start_tx": 90052801,
                            "genomic_end_tx": 90053119,
                            "abs_start_CDS": 0,
                            "abs_end_CDS": 0
                        }, {
                            "transcript_id": "NM_001287086.1",
                            "order_in_transcript": 2,
                            "genomic_start_tx": 90053507,
                            "genomic_end_tx": 90053609,
                            "abs_start_CDS": 0,
                            "abs_end_CDS": 0
                        }, {
                            "transcript_id": "NM_001287086.1",
                            "order_in_transcript": 3,
                            "genomic_start_tx": 90058484,
                            "genomic_end_tx": 90058651,
                            "abs_start_CDS": 1,
                            "abs_end_CDS": 126
                        }, {
                            "transcript_id": "NM_001287086.1",
                            "order_in_transcript": 4,
                            "genomic_start_tx": 90058741,
                            "genomic_end_tx": 90058800,
                            "abs_start_CDS": 127,
                            "abs_end_CDS": 185
                        }, {
                            "transcript_id": "NM_001287086.1",
                            "order_in_transcript": 5,
                            "genomic_start_tx": 90061637,
                            "genomic_end_tx": 90063341,
                            "abs_start_CDS": 186,
                            "abs_end_CDS": 381
                        }],
                        "protein": {
                            "protein_id": "NP_001274015.1",
                            "description": "uncharacterized protein C1orf43 homolog isoform 3 [Mus musculus]",
                            "synonyms": "uncharacterized protein C1orf43 homolog",
                            "length": 126,
                            "ensembl_id": "",
                            "uniprot_id": "",
                            "gene_id": "99650",
                            "transcript_id": "NM_001287086.1"
                        },
                        "domains": [{
                            "protein_id": "NP_001274015.1",
                            "type_id": 23438,
                            "AA_start": 2,
                            "AA_end": 61,
                            "nuc_start": 4,
                            "nuc_end": 183,
                            "total_length": 180,
                            "splice_junction": 1,
                            "complete_exon": 0,
                            "domainType": {
                                "type_id": 23438,
                                "name": "NICE-3",
                                "description": "NICE-3 protein; ",
                                "external_id": "pfam07406",
                                "CDD_id": 284755
                            }
                        }],
                        "spliceInDomains": [{
                            "transcript_id": "NM_001287086.1",
                            "exon_order_in_transcript": 3,
                            "type_id": 23438,
                            "total_length": 180,
                            "domain_nuc_start": 4,
                            "included_len": -123,
                            "exon_num_in_domain": 1
                        }, {
                            "transcript_id": "NM_001287086.1",
                            "exon_order_in_transcript": 4,
                            "type_id": 23438,
                            "total_length": 180,
                            "domain_nuc_start": 4,
                            "included_len": 57,
                            "exon_num_in_domain": 2
                        }]
                    }, {
                        "transcript_id": "NM_025762.3",
                        "tx_start": 90052801,
                        "tx_end": 90063341,
                        "cds_start": 90053053,
                        "cds_end": 90061833,
                        "gene_id": "99650",
                        "exon_count": 7,
                        "ensembl_ID": "ENSMUST00000160640.7",
                        "ucsc_id": "uc008qbc.4",
                        "protein_id": "NP_080038.1",
                        "transcriptExons": [{
                            "transcript_id": "NM_025762.3",
                            "order_in_transcript": 1,
                            "genomic_start_tx": 90052801,
                            "genomic_end_tx": 90053119,
                            "abs_start_CDS": 1,
                            "abs_end_CDS": 66
                        }, {
                            "transcript_id": "NM_025762.3",
                            "order_in_transcript": 2,
                            "genomic_start_tx": 90053507,
                            "genomic_end_tx": 90053609,
                            "abs_start_CDS": 67,
                            "abs_end_CDS": 168
                        }, {
                            "transcript_id": "NM_025762.3",
                            "order_in_transcript": 3,
                            "genomic_start_tx": 90056206,
                            "genomic_end_tx": 90056324,
                            "abs_start_CDS": 169,
                            "abs_end_CDS": 286
                        }, {
                            "transcript_id": "NM_025762.3",
                            "order_in_transcript": 4,
                            "genomic_start_tx": 90056528,
                            "genomic_end_tx": 90056582,
                            "abs_start_CDS": 287,
                            "abs_end_CDS": 340
                        }, {
                            "transcript_id": "NM_025762.3",
                            "order_in_transcript": 5,
                            "genomic_start_tx": 90058484,
                            "genomic_end_tx": 90058651,
                            "abs_start_CDS": 341,
                            "abs_end_CDS": 507
                        }, {
                            "transcript_id": "NM_025762.3",
                            "order_in_transcript": 6,
                            "genomic_start_tx": 90058741,
                            "genomic_end_tx": 90058800,
                            "abs_start_CDS": 508,
                            "abs_end_CDS": 566
                        }, {
                            "transcript_id": "NM_025762.3",
                            "order_in_transcript": 7,
                            "genomic_start_tx": 90061637,
                            "genomic_end_tx": 90063341,
                            "abs_start_CDS": 567,
                            "abs_end_CDS": 762
                        }],
                        "protein": {
                            "protein_id": "NP_080038.1",
                            "description": "uncharacterized protein C1orf43 homolog isoform 1 [Mus musculus]",
                            "synonyms": "uncharacterized protein C1orf43 homolog",
                            "length": 253,
                            "ensembl_id": "ENSMUSP00000124028.1",
                            "uniprot_id": "Q8R092",
                            "gene_id": "99650",
                            "transcript_id": "NM_025762.3"
                        },
                        "domains": [{
                            "protein_id": "NP_080038.1",
                            "type_id": 23438,
                            "AA_start": 6,
                            "AA_end": 188,
                            "nuc_start": 16,
                            "nuc_end": 564,
                            "total_length": 549,
                            "splice_junction": 1,
                            "complete_exon": 0,
                            "domainType": {
                                "type_id": 23438,
                                "name": "NICE-3",
                                "description": "NICE-3 protein; ",
                                "external_id": "pfam07406",
                                "CDD_id": 284755
                            }
                        }],
                        "spliceInDomains": [{
                            "transcript_id": "NM_025762.3",
                            "exon_order_in_transcript": 1,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": -51,
                            "exon_num_in_domain": 1
                        }, {
                            "transcript_id": "NM_025762.3",
                            "exon_order_in_transcript": 2,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 102,
                            "exon_num_in_domain": 2
                        }, {
                            "transcript_id": "NM_025762.3",
                            "exon_order_in_transcript": 3,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 118,
                            "exon_num_in_domain": 3
                        }, {
                            "transcript_id": "NM_025762.3",
                            "exon_order_in_transcript": 4,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 54,
                            "exon_num_in_domain": 4
                        }, {
                            "transcript_id": "NM_025762.3",
                            "exon_order_in_transcript": 5,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 167,
                            "exon_num_in_domain": 5
                        }, {
                            "transcript_id": "NM_025762.3",
                            "exon_order_in_transcript": 6,
                            "type_id": 23438,
                            "total_length": 549,
                            "domain_nuc_start": 16,
                            "included_len": 57,
                            "exon_num_in_domain": 6
                        }]
                    }],
                    "geneExons": [{
                        "gene_id": "99650",
                        "genomic_start_tx": 90051635,
                        "genomic_end_tx": 90051693
                    }, {
                        "gene_id": "99650",
                        "genomic_start_tx": 90052600,
                        "genomic_end_tx": 90052785
                    }, {
                        "gene_id": "99650",
                        "genomic_start_tx": 90052801,
                        "genomic_end_tx": 90053119
                    }, {
                        "gene_id": "99650",
                        "genomic_start_tx": 90052899,
                        "genomic_end_tx": 90053119
                    }, {
                        "gene_id": "99650",
                        "genomic_start_tx": 90053507,
                        "genomic_end_tx": 90053609
                    }, {
                        "gene_id": "99650",
                        "genomic_start_tx": 90056206,
                        "genomic_end_tx": 90056324
                    }, {
                        "gene_id": "99650",
                        "genomic_start_tx": 90056528,
                        "genomic_end_tx": 90056582
                    }, {
                        "gene_id": "99650",
                        "genomic_start_tx": 90058484,
                        "genomic_end_tx": 90058651
                    }, {
                        "gene_id": "99650",
                        "genomic_start_tx": 90058741,
                        "genomic_end_tx": 90058800
                    }, {
                        "gene_id": "99650",
                        "genomic_start_tx": 90058741,
                        "genomic_end_tx": 90058867
                    }, {
                        "gene_id": "99650",
                        "genomic_start_tx": 90061637,
                        "genomic_end_tx": 90063341
                    }]
                }],
                "isExact": false
            }
        }

        //getting gene from results saved in site
        self.geneInfo = runGenesCreation(loadedGene, ignorePredictions)[0];
        $scope.transcripts = self.geneInfo.transcripts;
        $scope.geneName = self.geneInfo.gene_symbol;

        /* the showCanvas property defines the demands to view or hide each of the domain graphics. its
        default is to view all views*/
        $scope.showCanvas = {
            genomicView: [],
            transcriptView: [],
            proteinView: []
        };
        for (var i = 0; i < $scope.transcripts.length; i++) {
            $scope.showCanvas.genomicView[i] = true;
            $scope.showCanvas.transcriptView[i] = true;
            $scope.showCanvas.proteinView[i] = true;
        }
        //function that runs when the hide transcript button is clicked. its only hiding and not "re-showing" when clicked again
        $scope.changeTranscriptView = function (index) { //hide transcript. change name later
            $scope.showCanvas.genomicView[index] = false;
            $scope.showCanvas.transcriptView[index] = false;
            $scope.showCanvas.proteinView[index] = false;
        };

        //show only one view options. runs on the button "show only __"
        $scope.checkboxChecked = function () {
            var type = selectModeComboBox.value;
            if ($scope.viewMode == type) {
                return;
            }
            $scope.viewMode = type;
            if (type == "all") {
                $scope.canvasSize = 550;
            } else {
                $scope.canvasSize = 1000;
            }
            $(document).ready(function () {
                updateCanvases();
            });
            for (var i = 0; i < $scope.transcripts.length; i++) {
                if (type === "genomic") {
                    $scope.showCanvas.genomicView[i] = true;
                    $scope.showCanvas.transcriptView[i] = false;
                    $scope.showCanvas.proteinView[i] = false;
                } else if (type === "transcript") {
                    $scope.showCanvas.genomicView[i] = false;
                    $scope.showCanvas.transcriptView[i] = true;
                    $scope.showCanvas.proteinView[i] = false;
                } else if (type === "protein") {
                    $scope.showCanvas.genomicView[i] = false;
                    $scope.showCanvas.transcriptView[i] = false;
                    $scope.showCanvas.proteinView[i] = true;
                } else if (type === "all") {
                    $scope.showCanvas.genomicView[i] = true;
                    $scope.showCanvas.transcriptView[i] = true;
                    $scope.showCanvas.proteinView[i] = true;
                } else if (type === "transcript_protein") {
                    $scope.showCanvas.genomicView[i] = false;
                    $scope.showCanvas.transcriptView[i] = true;
                    $scope.showCanvas.proteinView[i] = true;
                }

            }
        }

        //for modals we need variable and function for opening:
        $scope.showWindow = undefined;
        $scope.openWindow = function (type, id) {
            $scope.showWindow = type;
            if (type == "transcript") {
                self.currTranscript = $scope.transcripts[id];
                self.currTranscript.tx_start = numberToTextWithCommas(self.currTranscript.tx_start);
                self.currTranscript.tx_end = numberToTextWithCommas(self.currTranscript.tx_end);
                self.currTranscript.cds_start = numberToTextWithCommas(self.currTranscript.cds_start);
                self.currTranscript.cds_end = numberToTextWithCommas(self.currTranscript.cds_end);
            } else if (type == "protein") {
                self.currTranscript = $scope.transcripts[id];
            }
        }

        //after every page-load or configuration change we create updated graphics 
        //a function which its purpose is to load the canvases' graphics only after the elements finished loading
        function updateCanvases() {
            for (var i = 0; i < $scope.transcripts.length; i++) {
                $('#fadeinDiv' + i).hide().fadeIn(1000 + Math.min(i * 500, 1000));
                buildGenomicView('canvas-genomic' + i, $scope.transcripts[i]);
                buildTranscriptView('canvas-transcript' + i, $scope.transcripts[i]);
                buildProteinView('canvas-protein' + i, $scope.transcripts[i]);
            }
            buildScaleView("canvas-scale", self.geneInfo.scale);
            buildScaleViewForProtein("canvas-scale-protein", self.geneInfo.proteinScale);
            createTooltipManager();
            $('#canvas-scale').hide().fadeIn(1000);
            $('#canvas-scale-protein').hide().fadeIn(1000);
            $('#genomic_range').ionRangeSlider({
                type: "double",
                min: self.geneInfo.scale.start,
                max: self.geneInfo.scale.end,
                from: self.geneInfo.scale.start,
                to: self.geneInfo.scale.end,
                grid: true,
                onFinish: function (data) {
                    self.geneInfo = createGraphicInfoForGene(loadedGene.genes[0], isReviewedCheckBox.checked, {
                        start: data.from,
                        end: data.to
                    });
                    $scope.transcripts = self.geneInfo.transcripts;
                    $scope.geneName = self.geneInfo.gene_symbol;
                    /*$scope.$apply();*/
                    $(document).ready(function () {
                        updateCanvases();
                    });

                }

            });
            $('#protein_range').ionRangeSlider({
                type: "double",
                min: 0,
                max: self.geneInfo.proteinScale.length,
                from: 0,
                to: self.geneInfo.proteinScale.length,
                grid: true,
                onFinish: function (data) {
                    self.geneInfo = createGraphicInfoForGene(loadedGene.genes[0], isReviewedCheckBox.checked, {
                        proteinStart: data.from,
                        proteinEnd: data.to
                    });
                    $scope.transcripts = self.geneInfo.transcripts;
                    $scope.geneName = self.geneInfo.gene_symbol;
                    /*$scope.$apply();*/
                    $(document).ready(function () {
                        updateCanvases();
                    });

                }

            });
            $("canvas")
                .mousemove(function (event) {
                    showTextValues = showText(event);
                    if (showTextValues[0]) {
                        $("#myTooltip").show();
                        $("#myTooltip").css("top", event.pageY + 2);
                        $("#myTooltip").css("left", event.pageX + 2);
                        $("#myTooltip").html(showTextValues[1]);
                    } else {
                        $("#myTooltip").hide();
                    }
                });
            //when to show modal
            function showText(event) {
                res = [false, ""];
                if (self.toolTipManagerForCanvas[event.target.id] != undefined) {
                    offset = event.target.getBoundingClientRect();
                    exon = self.toolTipManagerForCanvas[event.target.id];
                    for (var i = 0; i < exon.length; i++) {
                        if (event.clientX - offset.left >= exon[i][0] && event.clientX - offset.left <= exon[i][0] + exon[i][2] &&
                            event.clientY - offset.top >= exon[i][1] && event.clientY - offset.top <= exon[i][1] + exon[i][3]) {
                            return [true, exon[i][4]];
                        }
                    }
                }
                return res;
            }

        }

        $scope.closeModalFromBackground = function (event) {
            if (event.target.id == 'BlackBackground') {
                $scope.showWindow = false
            }
        }

        $scope.chromosomeLocation = self.geneInfo.chromosome + ":" + numberToTextWithCommas(self.geneInfo.scale.start) + "-" + numberToTextWithCommas(self.geneInfo.scale.end);

        //zooming in by receiving new ends and calculating in between the new graphics
        self.zoomInFunction = function () {
            if (startWanted.value >= endWanted.value) {
                $window.alert("the start coordinate must be before the end coordinate");
                return;
            }
            self.geneInfo = createGraphicInfoForGene(loadedGene.genes[0], isReviewedCheckBox.checked, {
                start: startWanted.value,
                end: endWanted.value
            })
            $scope.transcripts = self.geneInfo.transcripts;
            $scope.geneName = self.geneInfo.gene_symbol;
            $(document).ready(function (self) {
                updateCanvases();
            });
        }
        $scope.filterUnreviewed = function () {
            $window.sessionStorage.setItem("ignorePredictions", "" + isReviewedCheckBox.checked);
            $route.reload();
        }
        $(document).ready(function (self) {
            updateCanvases();
        });

        /*
        for using tooltip we need for all canvases to hold information on areas for
        tooltip and the text wanted for them. this means we need to go over each
        exon or domain and look we it is drawn
        */
        function createTooltipManager() {
            self.toolTipManagerForCanvas = {};
            for (var i = 0; i < $scope.transcripts.length; i++) {
                
                var proteinCanvasID = "canvas-protein" + i;
                var transcriptCanvasID = "canvas-transcript" + i;
                var genomicCanvasID = "canvas-genomic" + i;
                self.toolTipManagerForCanvas[proteinCanvasID] = [];
                self.toolTipManagerForCanvas[transcriptCanvasID] = [];
                self.toolTipManagerForCanvas[genomicCanvasID] = [];
                
                for (var j = $scope.transcripts[i].domains.length - 1; j >= 0; j--) {
                    var domains = $scope.transcripts[i].domains;
                    var spacing = 25;
                    var canvasP = document.getElementById(proteinCanvasID);
                    var canvasWidth = canvasP.width;
                    var coordinatesWidth = ((canvasWidth - 50) / $scope.transcripts[i].shownLength);
                    //calculations
                    domainWidth = (domains[j].end - domains[j].start) * coordinatesWidth;
                    domainHeight = 45;
                    domainX = domains[j].start * coordinatesWidth;
                    domainY = spacing - domainHeight / 2;
                    self.toolTipManagerForCanvas[proteinCanvasID].push([domainX, domainY, domainWidth, domainHeight,getTooltipTextForDomain(domains[j])]);
                }
                for (j = 0; j < $scope.transcripts[i].exons.length; j++) {
                    var exons = $scope.transcripts[i].exons;
                    var canvasE = document.getElementById(transcriptCanvasID);
                    var canvasHeight = canvasE.height;
                    var canvasWidth = canvasE.width;
                    var lineThickness = 4;
                    var spacing = (canvasHeight - lineThickness) / 2; //devide by 2 so its the middle
                    var coordinatesWidth = ((canvasWidth - 50) / $scope.transcripts[i].shownLength);
                    exonWidth = (exons[j].exonViewEnd - exons[j].exonViewStart + 1) * coordinatesWidth;
                    exonHeight = 25;
                    exonX = exons[j].exonViewStart * coordinatesWidth; //currX;
                    exonY = spacing - exonHeight / 2;
                    if (exonX + exonWidth >= canvasWidth) {
                        exonWidth = Math.max(1, canvasWidth - exonX - 2);
                    }
                    self.toolTipManagerForCanvas[transcriptCanvasID].push([exonX, exonY, exonWidth, exonHeight, "exon: " + exons[j].orderInTranscript+"/"+exons.length]);
                }
                for (j = 0; j < $scope.transcripts[i].exons.length; j++) {
                    var exons = $scope.transcripts[i].exons;
                    var canvasT = document.getElementById(genomicCanvasID); 
                    var canvasHeight = canvasT.height;
                    var canvasWidth = canvasT.width;
                    var lineThickness = 2;
                    var spacing = 50;
                    var lengthOfGene = $scope.transcripts[i].length;
                    var beginningEmpty=10; //in pixels
                    var endEmpty=5; //in pixels
                    var coordinatesWidth = (canvasT.width-beginningEmpty-endEmpty) / lengthOfGene;
                    var exonWidth = Math.max(3, (exons[j].transcriptViewEnd - exons[j].transcriptViewStart + 1) * coordinatesWidth);
                    const exonHeight = 70;
                    const exonX = exons[j].transcriptViewStart * coordinatesWidth+beginningEmpty;
                    const exonY = spacing - exonHeight / 2;
                    if (exonX + exonWidth >= canvasWidth) {
                        exonWidth = Math.max(1, canvasWidth - exonX - 2);
                    }
                    self.toolTipManagerForCanvas[genomicCanvasID].push([exonX, exonY, exonWidth, exonHeight, "exon: " + exons[j].orderInTranscript+"/"+exons.length]);
                }
            }
        }

        function getTooltipTextForDomain(domain){
            var name=domain.name;
            var start=domain.AAstart;
            var end=domain.AAend;
            var length=end-start;
            var source=domain.source;
            if(source==undefined){
                source="unknown";
            }
            return  "<u>"+name+"</u><br> positions: "+start+"-"+end+"<br>length: "+length+"<br>source: "+source;



        }
    });