/* this controller for the result page should handle different view options and previwing the 
graphics properly when the page loads. It should also allow tooltips of kinds and windows if needed. */
angular.module("DoChaP")
    .controller("resultsController", function ($scope, $window, $route, $routeParams, webService, querySearchService) {

        //needed in case of failure css wont show. if not fail it will reach here
        $('#searchExists').css("display", "block");

        self = this;
        $scope.noSearch = false;
        $scope.loadingText = false;
        var loadedGene = JSON.parse($window.sessionStorage.getItem("currGene"));
        var ignorePredictions = JSON.parse($window.sessionStorage.getItem("ignorePredictions"));
        isReviewedCheckBox.checked = ignorePredictions;
        $scope.canvasSize = 550;
        $scope.viewMode = "all";
        self.toolTipManagerForCanvas = {};
        
        if($routeParams.specie!=undefined &&$routeParams.query!=undefined){
            isReviewed=true;
            querySearchService.queryHandler($routeParams.query, $routeParams.specie, isReviewed);   
        }
        if (loadedGene == undefined) {
            $scope.noSearch = true;
            return;
        }

        //getting gene from results saved in site
        self.geneInfo = runGenesCreation(loadedGene, ignorePredictions)[0];
        $scope.transcripts = self.geneInfo.transcripts;

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
        $scope.hideTranscriptView = function (index) { //hide transcript. change name later
            $scope.showCanvas.genomicView[index] = false;
            $scope.showCanvas.transcriptView[index] = false;
            $scope.showCanvas.proteinView[index] = false;
        };

        //show according to mode
        $scope.showTranscriptView = function (index) { 
            var type=$scope.viewMode;
            if (type === "genomic") {
                $scope.showCanvas.genomicView[index] = true;
                $scope.showCanvas.transcriptView[index] = false;
                $scope.showCanvas.proteinView[index] = false;
            } else if (type === "transcript") {
                $scope.showCanvas.genomicView[index] = false;
                $scope.showCanvas.transcriptView[index] = true;
                $scope.showCanvas.proteinView[index] = false;
            } else if (type === "protein") {
                $scope.showCanvas.genomicView[index] = false;
                $scope.showCanvas.transcriptView[index] = false;
                $scope.showCanvas.proteinView[index] = true;
            } else if (type === "all") {
                $scope.showCanvas.genomicView[index] = true;
                $scope.showCanvas.transcriptView[index] = true;
                $scope.showCanvas.proteinView[index] = true;
            } else if (type === "transcript_protein") {
                $scope.showCanvas.genomicView[index] = false;
                $scope.showCanvas.transcriptView[index] = true;
                $scope.showCanvas.proteinView[index] = true;
            }
        };

        //show only one view options. runs on the button "show only __"
        $scope.checkboxChecked = function () {
            webService.userLog("partial_view");
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
            $('#BlackBackground').css('display', 'block');
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
            webService.userLog("open_window");
            $(document).ready(function () {
                dragElement(document.getElementById("myModal"));
                $scope.$apply();
            });
            
        }

        //after every page-load or configuration change we create updated graphics 
        //a function which its purpose is to load the canvases' graphics only after the elements finished loading
        function updateCanvases() {
            for (var i = 0; i < $scope.transcripts.length; i++) {
                $('#fadeinDiv' + i).hide().fadeIn(1000 + Math.min(i * 500, 1000));
                $scope.transcripts[i].show('canvas-genomic' + i, 'canvas-transcript' + i, 'canvas-protein' + i, self.toolTipManagerForCanvas, 'canvas-protein-extend' + i);
            }
            self.geneInfo.scale.draw("canvas-scale");

            //=========GRIDLINES IMPORTANT==========
            self.geneInfo.scale.drawBehind("gridlines");
            
            self.geneInfo.proteinScale.draw("canvas-scale-protein");
            // createTooltipManager();
            $('#canvas-scale').hide().fadeIn(1000);
            $('#canvas-scale-protein').hide().fadeIn(1000);
            $('#genomic_range').ionRangeSlider({
                type: "double",
                min: self.geneInfo.scale.start,
                max: self.geneInfo.scale.end,
                from: self.geneInfo.scale.start,
                to: self.geneInfo.scale.end,
                drag_interval: true,
                grid: true,
                onFinish: function (data) {
                    self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, data.from, data.to, self.geneInfo.proteinStart, self.geneInfo.proteinEnd);
                    $scope.transcripts = self.geneInfo.transcripts;
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
                drag_interval: true,
                grid: true,
                onFinish: function (data) {
                    self.geneInfo = new Gene(loadedGene.genes[0], isReviewedCheckBox.checked, undefined, self.geneInfo.start, self.geneInfo.end, data.from, data.to);
                    $scope.transcripts = self.geneInfo.transcripts;
                    /*$scope.$apply();*/
                    $(document).ready(function () {
                        updateCanvases();
                    });

                }

            });
            $('canvas').click(function (event) {
                var tooltipManager=self.toolTipManagerForCanvas;
                var showTextValues = Transcript.showText(event,tooltipManager);
                if (showTextValues[0]) {
                     if (showTextValues[2] != undefined) {
                        $window.open(Species.getURLfor(showTextValues[2]), '_blank');
                    } else if (tooltipManager[event.target.id + "object"] != undefined) {
                        tooltipManager[event.target.id + "object"].proteinExtendView = !tooltipManager[event.target.id + "object"].proteinExtendView;
                       $scope.$apply();

                    }

                }
            });
        }

        $scope.closeModalFromBackground = function (event) {
            if (event.target.id == 'BlackBackground') {
                $scope.showWindow = false
            }
        }

        $scope.chromosomeLocation = self.geneInfo.chromosome + ":" + numberToTextWithCommas(self.geneInfo.scale.start) + "-" + numberToTextWithCommas(self.geneInfo.scale.end);

        // //zooming in by receiving new ends and calculating in between the new graphics
        // self.zoomInFunction = function () {
        //     if (startWanted.value >= endWanted.value) {
        //         $window.alert("the start coordinate must be before the end coordinate");
        //         return;
        //     }
        //     // self.geneInfo = createGraphicInfoForGene(loadedGene.genes[0], isReviewedCheckBox.checked, {
        //     //     start: startWanted.value,
        //     //     end: endWanted.value
        //     // })
        //     self.geneInfo=new Gene(loadedGene.genes[0], isReviewedCheckBox.checked,undefined,startWanted.value,endWanted.value,undefined,undefined);
        //     $scope.transcripts = self.geneInfo.transcripts;
        //     $(document).ready(function (self) {
        //         updateCanvases();
        //     });
        // }
        $scope.filterUnreviewed = function () {
            $window.sessionStorage.setItem("ignorePredictions", "" + isReviewedCheckBox.checked);
            $route.reload();
        }
        $(document).ready(function (self) {
            updateCanvases();
        });

        //9.3.20
        /*
        for using tooltip we need for all canvases to hold information on areas for
        tooltip and the text wanted for them. this means we need to go over each
        exon or domain and look we it is drawn
        */
        // function createTooltipManager() {
        //     // self.toolTipManagerForCanvas = {};
        //     for (var i = 0; i < $scope.transcripts.length; i++) {

        //         // var proteinCanvasID = "canvas-protein" + i;
        //         // var transcriptCanvasID = "canvas-transcript" + i;
        //         // var genomicCanvasID = "canvas-genomic" + i;

        //         // self.toolTipManagerForCanvas[proteinCanvasID] = [];
        //         // self.toolTipManagerForCanvas[transcriptCanvasID] = [];
        //         // self.toolTipManagerForCanvas[genomicCanvasID] = [];

        //         //protein (view) tooltip
        //         // var domains = $scope.transcripts[i].domains;
        //         // var startHeight = 25;
        //         // var canvasP = document.getElementById(proteinCanvasID);
        //         // var canvasWidth = canvasP.width;
        //         // var coordinatesWidth = ((canvasWidth - 50) / $scope.transcripts[i].shownLength);

        //         // for (var j = domains.length - 1; j >= 0; j--) {
        //         //     var tooltipData = domains[j].tooltip(coordinatesWidth, startHeight);
        //         //     self.toolTipManagerForCanvas[proteinCanvasID].push(tooltipData);
        //         // }

        //         //transcript tooltip
        //         // var canvasE = document.getElementById(transcriptCanvasID);
        //         // var canvasHeight = canvasE.height;
        //         // var canvasWidth = canvasE.width;
        //         // var lineThickness = 4;
        //         // var startHeight = (canvasHeight - lineThickness) / 2; //devide by 2 so its the middle
        //         // var coordinatesWidth = ((canvasWidth - 50) / $scope.transcripts[i].shownLength);
        //         // for (j = 0; j < $scope.transcripts[i].exons.length; j++) {
        //         //     var tooltipData = $scope.transcripts[i].exons[j].transcriptTooltip(coordinatesWidth, canvasWidth, startHeight)
        //         //     self.toolTipManagerForCanvas[transcriptCanvasID].push(tooltipData);
        //         // }

        //         // //genomic tooltip
        //         // var startHeight = 50;
        //         // var canvas = document.getElementById(genomicCanvasID);
        //         // var canvasWidth = canvas.width;
        //         // var beginningEmpty = 10; //in pixels
        //         // var endEmpty = 5; //in pixels
        //         // var lengthOfGene = $scope.transcripts[i].length;
        //         // var spaceAfterCut = 50;
        //         // var coordinatesWidth = (canvas.width - beginningEmpty - endEmpty) / lengthOfGene;
        //         // if($scope.transcripts[i].gene.cutOffStart != -1 && $scope.transcripts[i].gene.cutOffLength!=-1){
        //         //     coordinatesWidth = (canvas.width - beginningEmpty - endEmpty - spaceAfterCut) / (lengthOfGene-$scope.transcripts[i].gene.cutOffLength);
        //         // }
        //         // var isStrandNegative = $scope.transcripts[i].isStrandNegative;
        //         // for (j = 0; j < $scope.transcripts[i].exons.length; j++) {
        //         //     var tooltipData = $scope.transcripts[i].exons[j].genomicTooltip(startHeight, coordinatesWidth, beginningEmpty, endEmpty, canvasWidth, isStrandNegative)
        //         //     self.toolTipManagerForCanvas[genomicCanvasID].push(tooltipData);
        //         // }
        //     }
        // }

        $scope.numberToTextWithCommas=numberToTextWithCommas;
    });