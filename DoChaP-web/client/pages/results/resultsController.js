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
        var isStart = true;
        self = this;
        $scope.noSearch = false;
        $scope.loadingText = false;
        var loadedGene = JSON.parse($window.sessionStorage.getItem("currGene"));
        $scope.ignorePredictions = JSON.parse($window.sessionStorage.getItem("ignorePredictions"));
        $scope.canvasSize = 550;
        $scope.viewMode = "all";
        self.toolTipManagerForCanvas = {};
        $scope.numberToTextWithCommas = numberToTextWithCommas;

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
        $scope.display.TranscriptDisplayManager.addTranscripts($scope.transcripts);
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
        });


        //when "hide transcript" button is clicked.
        $scope.hideTranscriptView = function (index) {
            $scope.display.TranscriptDisplayManager.hideTranscriptByIndex(index);
            countShownTranscripts();
        };

        //when "show transcript" button is clicked or when mode changes
        $scope.showTranscriptView = function(index){
            $scope.display.TranscriptDisplayManager.showTranscript(index, $scope.viewMode);
            countShownTranscripts();
        }

        //count the number of transcripts shown
        function countShownTranscripts() {
            var counter = 0;
            for (var i = 0; i < $scope.transcripts.length; i++) {
                if ($scope.transcripts[i].genomicView ||
                    $scope.transcripts[i].transcriptView ||
                    $scope.transcripts[i].proteinView) {
                    counter = counter + 1;
                }
            }
            $scope.shownTranscripts = counter;
            $scope.hiddenTranscripts = $scope.transcripts.length - counter;
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
            $scope.display.TranscriptDisplayManager.changeViewMode(type);
            countShownTranscripts();
            $(document).ready(function () {
                updateCanvases();
            });
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
            //drawing all transcripts
            for (var i = 0; i < $scope.transcripts.length; i++) {
                if (isStart) {
                    $('#fadeinDiv' + i).hide().fadeIn(1000 + Math.min(i * 500, 1000));
                }
                $scope.transcripts[i].show('canvas-genomic' + i, 'canvas-transcript' + i, 'canvas-protein' + i, self.toolTipManagerForCanvas, 'canvas-protein-extend' + i);
            }

            //drawing scales
            self.geneInfo.scale.draw("canvas-scale");
            self.geneInfo.scale.drawBehind("genomicGridlines");
            self.geneInfo.proteinScale.drawBehind("proteinGridlines");
            self.geneInfo.proteinScale.draw("canvas-scale-protein");
            $('#canvas-scale');
            $('#canvas-scale-protein');
            isStart = false; //needed for fade in animations to stop from now on

            createRangeSliders();

            //events on click
            $('canvas').click(function (event) {
                var tooltipManager = self.toolTipManagerForCanvas;
                var showTextValues = Transcript.showText(event, tooltipManager);
                if (showTextValues[0]) {
                    if (showTextValues[2] == 'click' && tooltipManager[event.target.id + "object"] != undefined) {
                        tooltipManager[event.target.id + "object"].proteinExtendView = !tooltipManager[event.target.id + "object"].proteinExtendView;
                        $scope.$apply();
                    }
                }
            });

        }

        function createRangeSliders() {
            var onFinishWhenStrandPositive = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, data.from, data.to, self.geneInfo.proteinStart, self.geneInfo.proteinEnd);
                $scope.transcripts = self.geneInfo.transcripts;
                $(document).ready(function () {
                    updateCanvases();
                });
            };

            var onFinishWhenStrandNegative = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, self.maximumRange - data.to, self.maximumRange - data.from, self.geneInfo.proteinStart, self.geneInfo.proteinEnd);
                $scope.transcripts = self.geneInfo.transcripts;
                $(document).ready(function () {
                    updateCanvases();
                });
            }

            var OnFinishProtein = function (data) {
                self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, self.geneInfo.start, self.geneInfo.end, data.from, data.to);
                $scope.transcripts = self.geneInfo.transcripts;
                $(document).ready(function () {
                    updateCanvases();
                })};

            $scope.display.locationScopeChanger.updateGenomiclocationScopeChanger(
                '#genomic_range', self.geneInfo.scale, $scope.strand, onFinishWhenStrandPositive, onFinishWhenStrandNegative,
                self.maximumRange, self.minimumRange);

            $scope.display.locationScopeChanger.updateProteinlocationScopeChanger(
                '#protein_range', OnFinishProtein, self.geneInfo.proteinScale.length);
        }

        //downloading pdf
        $scope.downloadPDF = function () {
            $scope.display.pdfCreator.create(self.geneInfo,"");
        }
    });