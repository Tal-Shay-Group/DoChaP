/*
this controller for the result page should handle different view options
 and previwing the graphics properly when the page loads.
 It should also allow tooltips of kinds and windows if needed.
*/
angular.module("DoChaP")
    .controller("resultsController", function ($scope, $window, $route, $routeParams, webService, querySearchService) {

        //needed in case of failure css wont show. if not fail it will reach here
        $('#searchExists').css("display", "block");

        //init attributes
        $scope.display = new Display();
        self = this;
        $scope.noSearch = false;
        var loadedGene = JSON.parse($window.sessionStorage.getItem("currGene"));
        $scope.ignorePredictions = JSON.parse($window.sessionStorage.getItem("ignorePredictions"));
        $scope.canvasSize = 550;
        $scope.viewMode = "all";
        self.toolTipManagerForCanvas = {};
        $scope.numberToTextWithCommas = numberToTextWithCommas;
        $scope.modeModel = "all";

        //if input is in website path
        if ($routeParams.specie != undefined && $routeParams.query != undefined) {
            isReviewed = true;
            querySearchService.queryHandler($routeParams.query, $routeParams.specie, isReviewed);
        }

        //if no search found
        if (loadedGene == undefined) {
            $scope.noSearch = true;
            return;
        }

        //getting gene from results saved in website memory
        self.geneInfo = runGenesCreation(loadedGene, $scope.ignorePredictions)[0];
        $scope.transcripts = self.geneInfo.transcripts;
        $scope.display.transcriptDisplayManager.addTranscripts($scope.transcripts);
        $scope.shownTranscripts = $scope.transcripts.length;
        $scope.hiddenTranscripts = 0;
        $scope.strand = self.geneInfo.strand;

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
            
            var updateWithGenomicInformationAfterFinish = function(gene){
                $scope.display.transcriptDisplayManager.addTranscripts(self.geneInfo.transcripts);
                $scope.display.transcriptDisplayManager.changeViewMode($scope.viewMode);
                $scope.transcripts = self.geneInfo.transcripts;
                updateCanvases();
            }
            
            var onFinishGenomicWithStrandPositive = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, data.from, data.to, self.geneInfo.proteinStart, self.geneInfo.proteinEnd);
                updateWithGenomicInformationAfterFinish(self.geneInfo);
            };

            var onFinishGenomicWithStrandNegative = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, self.maximumRange - data.to, self.maximumRange - data.from, self.geneInfo.proteinStart, self.geneInfo.proteinEnd);
                updateWithGenomicInformationAfterFinish(self.geneInfo);
            }

            var OnFinishProtein = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, self.geneInfo.start, self.geneInfo.end, data.from, data.to);
                updateWithGenomicInformationAfterFinish(self.geneInfo);
            };

            $scope.display.locationScopeChanger.updateGenomiclocationScopeChanger(
                '#genomic_range', self.geneInfo.scale, $scope.strand, onFinishGenomicWithStrandPositive, onFinishGenomicWithStrandNegative,
                self.maximumRange, self.minimumRange);

            $scope.display.locationScopeChanger.updateProteinlocationScopeChanger(
                '#protein_range', OnFinishProtein, self.geneInfo.proteinScale.length);
        }

        //downloading pdf
        $scope.downloadPDF = function () {
            $scope.display.pdfCreator.create(self.geneInfo, "");
        }

        //zoom genomic via button, direction can be "In" or "Out"
        $scope.onZoomButtonGenomicClick = function(direction){
            var updateWithGenomicInformationAfterFinish = function(){
                $scope.display.transcriptDisplayManager.addTranscripts(self.geneInfo.transcripts);
                $scope.display.transcriptDisplayManager.changeViewMode($scope.viewMode);
                $scope.transcripts = self.geneInfo.transcripts;
                updateCanvases();
            }
            
            var onFinishGenomicWithStrandPositive = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, data.from, data.to, self.geneInfo.proteinStart, self.geneInfo.proteinEnd);
                updateWithGenomicInformationAfterFinish(self.geneInfo);
            };

            var onFinishGenomicWithStrandNegative = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, self.maximumRange - data.to, self.maximumRange - data.from, self.geneInfo.proteinStart, self.geneInfo.proteinEnd);
                updateWithGenomicInformationAfterFinish(self.geneInfo);
            }

            $scope.display.locationScopeChanger.zoomGenomicWithButton( $scope.strand, self.geneInfo.scale, direction , onFinishGenomicWithStrandPositive, onFinishGenomicWithStrandNegative, "#genomic_range", self.geneInfo)
        }

        $scope.onZoomButtonProteinClick = function(direction){
            var updateWithGenomicInformationAfterFinish = function(){
                $scope.display.transcriptDisplayManager.addTranscripts(self.geneInfo.transcripts);
                $scope.display.transcriptDisplayManager.changeViewMode($scope.viewMode);
                $scope.transcripts = self.geneInfo.transcripts;
                updateCanvases();
            }

            var OnFinishProtein = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, self.geneInfo.start, self.geneInfo.end, data.from, data.to);
                updateWithGenomicInformationAfterFinish(self.geneInfo);
            };

            $scope.display.locationScopeChanger.zoomProteinWithButton(self.geneInfo.proteinScale, direction, OnFinishProtein, "#protein_range")
        }
    });