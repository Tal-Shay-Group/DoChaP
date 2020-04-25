/* this controller for the result page should handle different view options and previwing the 
graphics properly when the page loads. It should also allow tooltips of kinds and windows if needed. */
angular.module("DoChaP")
    .controller("resultsController", function ($scope, $window, $route, $routeParams, webService, querySearchService) {

        //needed in case of failure css wont show. if not fail it will reach here
        $('#searchExists').css("display", "block");
        var isStart = true;
        self = this;
        $scope.noSearch = false;
        $scope.loadingText = false;
        var loadedGene = JSON.parse($window.sessionStorage.getItem("currGene"));
        var ignorePredictions = JSON.parse($window.sessionStorage.getItem("ignorePredictions"));
        isReviewedCheckBox.checked = ignorePredictions;
        $scope.canvasSize = 550;
        $scope.viewMode = "all";
        self.toolTipManagerForCanvas = {};
        if ($routeParams.specie != undefined && $routeParams.query != undefined) {
            isReviewed = true;
            querySearchService.queryHandler($routeParams.query, $routeParams.specie, isReviewed);
        }
        if (loadedGene == undefined) {
            $scope.noSearch = true;
            return;
        }

        //getting gene from results saved in site
        self.geneInfo = runGenesCreation(loadedGene, ignorePredictions)[0];
        $scope.transcripts = self.geneInfo.transcripts;
        $scope.shownTranscripts = $scope.transcripts.length;
        $scope.hiddenTranscripts = 0;


        //when "hide transcript" button is clicked.
        $scope.hideTranscriptView = function (index) {
            $scope.transcripts[index].genomicView = false;
            $scope.transcripts[index].transcriptView = false;
            $scope.transcripts[index].proteinView = false;
            countShownTranscripts();
            // $scope.$apply();
        };

        //show according to mode
        $scope.showTranscriptView = function (index) {
            var type = $scope.viewMode;
            if (type === "genomic") {
                $scope.transcripts[index].genomicView = true;
                $scope.transcripts[index].transcriptView = false;
                $scope.transcripts[index].proteinView = false;
            } else if (type === "transcript") {
                $scope.transcripts[index].genomicView = false;
                $scope.transcripts[index].transcriptView = true;
                $scope.transcripts[index].proteinView = false;
            } else if (type === "protein") {
                $scope.transcripts[index].genomicView = false;
                $scope.transcripts[index].transcriptView = false;
                $scope.transcripts[index].proteinView = true;
            } else if (type === "all") {
                $scope.transcripts[index].genomicView = true;
                $scope.transcripts[index].transcriptView = true;
                $scope.transcripts[index].proteinView = true;
            } else if (type === "transcript_protein") {
                $scope.transcripts[index].genomicView = false;
                $scope.transcripts[index].transcriptView = true;
                $scope.transcripts[index].proteinView = true;
            }

            countShownTranscripts();

        };

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
            webService.userLog("partial_view");
            var type = selectModeComboBox.value;
            $scope.viewMode = type;
            if (type == "all") {
                $scope.canvasSize = 550;
            } else {
                $scope.canvasSize = 1000;
            }
            for (var i = 0; i < $scope.transcripts.length; i++) {
                $scope.showTranscriptView(i);
            }
            $(document).ready(function () {
                updateCanvases();
            });
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

        }

        $scope.closeModalFromBackground = function (event) {
            if (event.target.id == 'BlackBackground') {
                $scope.showWindow = false
            }
        }

        $scope.chromosomeLocation =  "chr"+self.geneInfo.chromosome + ":" + numberToTextWithCommas(self.geneInfo.scale.start) + "-" + numberToTextWithCommas(self.geneInfo.scale.end);
        $scope.filterUnreviewed = function () {
            $window.sessionStorage.setItem("ignorePredictions", "" + isReviewedCheckBox.checked);
            $route.reload();
        }

        $scope.numberToTextWithCommas = numberToTextWithCommas;

        //after every page-load or configuration change we create updated graphics 
        //a function which its purpose is to load the canvases' graphics only after the elements finished loading
        function updateCanvases() {
            for (var i = 0; i < $scope.transcripts.length; i++) {
                if (isStart) {
                    $('#fadeinDiv' + i).hide().fadeIn(1000 + Math.min(i * 500, 1000));
                }
                $scope.transcripts[i].show('canvas-genomic' + i, 'canvas-transcript' + i, 'canvas-protein' + i, self.toolTipManagerForCanvas, 'canvas-protein-extend' + i);
            }
            self.geneInfo.scale.draw("canvas-scale");
            self.geneInfo.scale.drawBehind("genomicGridlines");
            self.geneInfo.proteinScale.drawBehind("proteinGridlines");
            self.geneInfo.proteinScale.draw("canvas-scale-protein");
            $('#canvas-scale');
            $('#canvas-scale-protein');
            isStart = false;

            $('#genomic_range').ionRangeSlider({
                type: "double",
                skin: "square",
                min: self.geneInfo.scale.start,
                max: self.geneInfo.scale.end,
                from: self.geneInfo.scale.start,
                to: self.geneInfo.scale.end,
                drag_interval: true,
                // grid: true,
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
                skin: "square",
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

        $(document).ready(function () {
            updateCanvases();
        });

        $scope.downloadPDF = function () {
            var doc = new jsPDF();
            var space = 5;
            var width = 90;
            var height = 15;
            var rowHeight = 40;
            var startY = 40;
            var transcriptsPerPage=6;
            doc.text(space * 2, 2 * space, "Species: " + self.geneInfo.specieName + " Gene: " + self.geneInfo.gene_symbol + " total number of transcripts: " + $scope.transcripts.length);
            doc.text(space * 2, 4 * space, "chr"+self.geneInfo.chromosome + ":" + numberToTextWithCommas(self.geneInfo.scale.start) + "-" + numberToTextWithCommas(self.geneInfo.scale.end));
            var canvasScaleGenomic = document.getElementById("canvas-scale");
            var imgGenomicScale = canvasScaleGenomic.toDataURL("image/png");
            var canvasScaleProtein = document.getElementById("canvas-scale-protein");
            var imgProteinScale = canvasScaleProtein.toDataURL("image/png");

            doc.addImage(imgGenomicScale, space, 4.5 * space , width, height);
            doc.addImage(imgProteinScale, space + width + space ,4.5 * space , width, height);
                

            for (var i = 0; i < $scope.transcripts.length; i++) {

                var canvasGenomic = document.getElementById("canvas-genomic" + i);
                var imgGenomic = canvasGenomic.toDataURL("image/png");
                var canvasTranscript = document.getElementById("canvas-transcript" + i);
                var imgTranscript = canvasTranscript.toDataURL("image/png");
                var canvasProtein = document.getElementById("canvas-protein" + i);
                var imgProtein = canvasProtein.toDataURL("image/png");
                doc.setFontSize(10);
                doc.text(space, startY + rowHeight * (i % transcriptsPerPage), "Transcript: " + $scope.transcripts[i].name + " Protein: " + $scope.transcripts[i].protein_name);
                //x,y,width,height
                doc.addImage(imgGenomic, space, startY + space + rowHeight * (i % transcriptsPerPage), width, height);
                doc.addImage(imgTranscript, space + width + space, startY + space + rowHeight * (i % transcriptsPerPage), width, height / 2);
                doc.addImage(imgProtein, space + width + space, startY + space + rowHeight * (i % transcriptsPerPage) + height, width, height);

                if ((i + 1) % transcriptsPerPage == 0) {
                    doc.addPage();
                }

            }
            doc.save(self.geneInfo.gene_symbol + ".pdf");
        }
    });