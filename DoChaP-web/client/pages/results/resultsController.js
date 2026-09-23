/*
this controller for the result page should handle different view options
 and previwing the graphics properly when the page loads.
 It should also allow tooltips of kinds and windows if needed.
*/
angular.module("DoChaP")
    .controller("resultsController", function ($scope, $window, $route, $routeParams, webService, querySearchService) {

        //init attributes
        $scope.display = new Display();
        self = this;
        $scope.noSearch = false;
        $scope.searching = false;
        $scope.searchError = undefined;

        //A deep link - /results/:specie/:query - carries nothing in sessionStorage
        //but a PREVIOUS search's gene, so nothing may be drawn from it on this pass:
        //the page would paint the old gene (or "No gene has been found") and correct
        //itself a moment later. Run the query, show the spinner, and stop here. On
        //success queryHandler redirects to #!/results, which runs this controller
        //again - and by then currGene is the gene that was actually asked for.
        if ($routeParams.specie != undefined && $routeParams.query != undefined) {
            $scope.searching = true;
            $scope.query = $routeParams.query;
            querySearchService.queryHandler($routeParams.query, $routeParams.specie, true,
                                            undefined, $routeParams.transcripts)
                .then(function (result) {
                    //Only a failure lands here - success has already redirected.
                    //Without this a mistyped gene in a URL would spin for ever.
                    if (result != undefined && result[0] == "error") {
                        $scope.searching = false;
                        $scope.noSearch = true;
                        $scope.searchError = result[1];
                        $scope.$applyAsync();
                    }
                });
            return;
        }

        //needed in case of failure css wont show. if not fail it will reach here
        $('#searchExists').css("display", "block");

        var loadedGene = JSON.parse($window.sessionStorage.getItem("currGene"));
        $scope.ignorePredictions = JSON.parse($window.sessionStorage.getItem("ignorePredictions"));
        $scope.canvasSize = 550;
        $scope.viewMode = "all";
        self.toolTipManagerForCanvas = {};
        $scope.numberToTextWithCommas = numberToTextWithCommas;
        $scope.modeModel = "all";

        //if no search found
        if (loadedGene == undefined) {
            $scope.noSearch = true;
            return;
        }

        //Hand the DOMAS row's transcripts to Gene before it is built, so its two
        //filters - protein-coding only, and "hide predicted records" - let them
        //through. Always assigned, [] included, so an ordinary search resets it.
        Gene.alwaysShow = readDomasTranscripts();

        //getting gene from results saved in website memory
        self.geneInfo = runGenesCreation(loadedGene, $scope.ignorePredictions)[0];
        $scope.transcripts = self.geneInfo.transcripts;
        $scope.display.transcriptDisplayManager.addTranscripts($scope.transcripts);
        $scope.shownTranscripts = $scope.transcripts.length;
        $scope.hiddenTranscripts = 0;
        $scope.strand = self.geneInfo.strand;
        initDomasFilter();

        //for genomic slider to know the limits
        self.maximumRange = self.geneInfo.end;
        self.minimumRange = self.geneInfo.start;

        //for genomic slider to know the direction of numbers
        $scope.genomicClass = $scope.display.locationScopeChanger.getChangerClassForStrand($scope.strand);

        $scope.chromosomeLocation = "chr" + self.geneInfo.chromosome + ":" + numberToTextWithCommas(self.geneInfo.scale.start) + "-" + numberToTextWithCommas(self.geneInfo.scale.end);
        $(document).ready(function () {
            updateCanvases();
            createRangeSliders();
        });

        //when "hide transcript" button is clicked.
        $scope.hideTranscriptView = function (index) {
            $scope.display.transcriptDisplayManager.hideTranscriptByIndex(index);
            countShownTranscripts();
        };

        //when "show transcript" button is clicked or when mode changes
        $scope.showTranscriptView = function (index) {
            $scope.display.transcriptDisplayManager.showTranscript(index, $scope.viewMode);
            countShownTranscripts();
            updateCanvases();
        }

        // ---- DOMAS deep link: show only the transcripts the row compared -----
        //
        //Matching is field against field, never against Transcript.id. DOMAS names
        //a transcript by its ensembl id and falls back to refseq; Transcript.js
        //does the reverse. For a transcript carrying both ids - 159,129 of the
        //829,732 in the database - the two sides therefore spell the SAME
        //transcript differently, and comparing the collapsed ids would drop about
        //one row in five while looking like it worked. Both fields are on the
        //Transcript, so testing both makes either side's preference irrelevant.
        function transcriptMatchesId(transcript, wanted) {
            return transcript.transcript_refseq_id === wanted ||
                   transcript.transcript_ensembl_id === wanted;
        }

        function readDomasTranscripts() {
            var raw = $window.sessionStorage.getItem("domasTranscripts");
            if (!raw) return [];
            return raw.split(',')
                      .map(function (id) { return id.trim(); })
                      .filter(function (id) { return id !== ''; });
        }

        //Why a transcript DOMAS compared is not on the page. Answered from the
        //SERVER's raw transcript list rather than from $scope.transcripts, because
        //the usual answer is that Gene.js dropped it before it ever became a
        //Transcript object - so it is absent from the list we would be searching.
        function missingReason(id) {
            var raw = (loadedGene && loadedGene.genes && loadedGene.genes[0] &&
                       loadedGene.genes[0].transcripts) || [];
            var row = null;
            for (var i = 0; i < raw.length; i++) {
                if (raw[i].transcript_refseq_id === id ||
                    raw[i].transcript_ensembl_id === id) { row = raw[i]; break; }
            }
            if (!row) return 'absent';
            //Gene.js keeps only transcripts carrying a protein, because the page
            //draws a protein and domain track for each one. Every DOMAS row whose
            //alternative has no protein is a non_coding_alternative row - in the
            //immune set, 1,911 rows, and all 1,911 of them - so this is the
            //expected outcome for that label, not a lookup failure.
            if (!(row.protein_refseq_id || row.protein_ensembl_id)) return 'noProtein';
            if ($scope.ignorePredictions && id.indexOf('XM_') === 0) return 'predicted';
            return 'unknown';
        }

        function initDomasFilter() {
            var wanted = readDomasTranscripts();
            $scope.domasFilter = wanted.length
                ? { wanted: wanted, missing: [], applied: false, missingReasons: [], noProtein: [] }
                : null;
            if ($scope.domasFilter) applyDomasFilter();
        }

        //Hides every transcript the DOMAS row did not compare. Called again after
        //each rebuild (zoom, exon click), because those construct fresh Transcript
        //objects whose three view flags all start true.
        function applyDomasFilter() {
            if (!$scope.domasFilter) return;
            var wanted = $scope.domasFilter.wanted;
            var transcripts = $scope.transcripts || [];

            $scope.domasFilter.missing = wanted.filter(function (id) {
                return !transcripts.some(function (t) { return transcriptMatchesId(t, id); });
            });
            //Say WHY each one is absent. "Not shown", with no reason, reads as a
            //broken page for what is usually the correct and expected result.
            $scope.domasFilter.missingReasons = $scope.domasFilter.missing.map(
                function (id) { return { id: id, reason: missingReason(id) }; });

            //Shown, but with an empty protein track: a transcript that codes for no
            //protein. Unexplained, an empty row reads as a rendering failure - it is
            //the finding a non_coding_alternative row is making.
            $scope.domasFilter.noProtein = transcripts.filter(function (t) {
                return !t.hasProtein &&
                       wanted.some(function (id) { return transcriptMatchesId(t, id); });
            }).map(function (t) { return t.name || t.id; });

            var keep = transcripts.filter(function (t) {
                return wanted.some(function (id) { return transcriptMatchesId(t, id); });
            });
            //Hiding everything would leave a blank page: at zero shown transcripts
            //countShownTranscripts() also skips drawing the gridlines. A filter that
            //matches nothing is therefore not applied at all, and the banner says so.
            $scope.domasFilter.applied = keep.length > 0;
            if ($scope.domasFilter.applied) {
                transcripts.forEach(function (t, index) {
                    if (keep.indexOf(t) === -1) {
                        $scope.display.transcriptDisplayManager.hideTranscriptByIndex(index);
                    }
                });
            }
            countShownTranscripts();
        }

        //"Show all transcripts" - drops the filter for good, so a reload or a
        //later visit to this gene is an ordinary gene page again.
        $scope.showAllTranscripts = function () {
            $window.sessionStorage.removeItem("domasTranscripts");
            $route.reload();
        };

        //count the number of transcripts shown
        function countShownTranscripts() {
            var results = $scope.display.transcriptDisplayManager.countShownTranscripts();
            $scope.shownTranscripts = results.shownTranscripts;
            $scope.hiddenTranscripts = results.hiddenTranscripts;
            $(document).ready(function () {
                if ($scope.shownTranscripts > 0) {
                    self.geneInfo.scale.drawBehind("genomicGridlines");
                    self.geneInfo.proteinScale.drawBehind("proteinGridlines");
                }
            });
        }

        //change view mode. When selecting from chociebox "show only __"
        $scope.checkboxChecked = function () {
            var type = selectModeComboBox.value;
            $scope.viewMode = type;
            if (type == "all") {
                $scope.canvasSize = 550;
            } else {
                $scope.canvasSize = 1000;
            }
            $scope.display.transcriptDisplayManager.changeViewMode(type);
            countShownTranscripts();
            updateCanvases();
        }

        //for modals, need type of window and id of the clicked object
        $scope.openWindow = function (type, id) {
            self.currTranscript = $scope.transcripts[id];
            $scope.display.modal.openWindow(type, self.currTranscript);
        }

        //when filtering/unfiltering unreviewed
        $scope.filterUnreviewed = function () {
            $window.sessionStorage.setItem("ignorePredictions", "" + isReviewedCheckBox.checked);
            $route.reload();
        }

        //after every page-load or configuration change we create updated graphics 
        //a function which its purpose is to load the canvases' graphics only after the elements finished loading
        function updateCanvases() {
            $scope.display.canvasUpdater.updateCanvas(self.geneInfo, self.toolTipManagerForCanvas, "", $scope);
        }

        function createRangeSliders() {

            var updateWithGenomicInformationAfterFinish = function (gene) {
                $scope.display.transcriptDisplayManager.addTranscripts(self.geneInfo.transcripts);
                $scope.display.transcriptDisplayManager.changeViewMode($scope.viewMode);
                $scope.transcripts = self.geneInfo.transcripts;
                //the rebuild replaced the Transcript objects - all visible again
                applyDomasFilter();
                updateCanvases();
            }

            var OnFinishProtein = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, self.geneInfo.start, self.geneInfo.end, data.from, data.to);
                updateWithGenomicInformationAfterFinish(self.geneInfo);
            };

            $scope.display.locationScopeChanger.updateGenomiclocationScopeChanger(
                '#genomic_range', self.geneInfo.scale, $scope.strand, $scope.onFinishGenomicWithStrandPositive, $scope.onFinishGenomicWithStrandNegative,
                self.maximumRange, self.minimumRange);

            $scope.display.locationScopeChanger.updateProteinlocationScopeChanger(
                '#protein_range', OnFinishProtein, self.geneInfo.proteinScale.length);
        }

        //downloading pdf
        $scope.downloadPDF = function () {
            $scope.display.pdfCreator.create(self.geneInfo, "");
        }

        //zoom genomic via button, direction can be "In" or "Out"
        $scope.onZoomButtonGenomicClick = function (direction) {
            $scope.display.locationScopeChanger.zoomGenomicWithButton($scope.strand, self.geneInfo.scale, direction, $scope.onFinishGenomicWithStrandPositive,$scope.onFinishGenomicWithStrandNegative, "#genomic_range", self.geneInfo)
        }

        $scope.onZoomButtonProteinClick = function (direction) {
            var updateWithGenomicInformationAfterFinish = function () {
                $scope.display.transcriptDisplayManager.addTranscripts(self.geneInfo.transcripts);
                $scope.display.transcriptDisplayManager.changeViewMode($scope.viewMode);
                $scope.transcripts = self.geneInfo.transcripts;
                //the rebuild replaced the Transcript objects - all visible again
                applyDomasFilter();
                updateCanvases();
            }

            var OnFinishProtein = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, self.geneInfo.start, self.geneInfo.end, data.from, data.to);
                updateWithGenomicInformationAfterFinish(self.geneInfo);
            };

            $scope.display.locationScopeChanger.zoomProteinWithButton(self.geneInfo.proteinScale, direction, OnFinishProtein, "#protein_range")
        }

        $scope.onExonClick = function (proteinStart, proteinEnd, genomicStart, genomicEnd) {
            var updateWithGenomicInformationAfterFinish = function () {
                $scope.display.transcriptDisplayManager.addTranscripts(self.geneInfo.transcripts);
                $scope.display.transcriptDisplayManager.changeViewMode($scope.viewMode);
                $scope.transcripts = self.geneInfo.transcripts;
                //the rebuild replaced the Transcript objects - all visible again
                applyDomasFilter();
                updateCanvases();
            }


            self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, genomicStart, genomicEnd, proteinStart, proteinEnd);
            updateWithGenomicInformationAfterFinish(self.geneInfo);

            //update scales
            $("#protein_range").data("ionRangeSlider").update({
                from: proteinStart,
                to: proteinEnd
            });
            $scope.display.locationScopeChanger.moveToSelectedGenomicRange($scope.strand, "#genomic_range", genomicStart, genomicEnd, $scope.onFinishGenomicWithStrandPositive, $scope.onFinishGenomicWithStrandNegative, self.geneInfo)
        }

        $scope.onFinishGenomicWithStrandPositive = function (data) {
            self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, data.from, data.to, self.geneInfo.proteinStart, self.geneInfo.proteinEnd);
            $scope.updateWithGenomicInformationAfterFinish(self.geneInfo);
        };

        $scope.onFinishGenomicWithStrandNegative = function (data) {
            self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, self.maximumRange - data.to, self.maximumRange - data.from, self.geneInfo.proteinStart, self.geneInfo.proteinEnd);
            $scope.updateWithGenomicInformationAfterFinish(self.geneInfo);
        };

        $scope.updateWithGenomicInformationAfterFinish = function (gene) {
            $scope.display.transcriptDisplayManager.addTranscripts(gene.transcripts);
            $scope.display.transcriptDisplayManager.changeViewMode($scope.viewMode);
            $scope.transcripts = gene.transcripts;
            //the rebuild replaced the Transcript objects - all visible again
            applyDomasFilter();
            updateCanvases();
        }
    });