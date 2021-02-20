class Display {
    constructor() {
        this.modal = new Object();
        this.modal.type = undefined;
        this.modal.openWindow = function (type, currentTranscript) {
            $('#BlackBackground').css('display', 'block');
            this.type = type;
            if (type == "transcript") {
                currentTranscript.tx_start = numberToTextWithCommas(currentTranscript.tx_start);
                currentTranscript.tx_end = numberToTextWithCommas(currentTranscript.tx_end);
                currentTranscript.cds_start = numberToTextWithCommas(currentTranscript.cds_start);
                currentTranscript.cds_end = numberToTextWithCommas(currentTranscript.cds_end);
            }
        };
        this.modal.closeWindowFromTheSide = function (event) {
            if (event.target.id == 'BlackBackground') {
                this.type = undefined;
            }
        }

        this.locationScopeChanger = new Object();

        //in the beginning this needs to be called and the result should be in the html tag in the class property
        this.locationScopeChanger.getChangerClassForStrand = function (strand) {
            if (strand == '+') {
                return "js-range-slider";
            } else {
                return "js-range-slider-reverse-fixed";
            }
        }
        this.locationScopeChanger.updateGenomiclocationScopeChanger = function (name, scale, strand, onFinishWhenStrandPositive, onFinishWhenStrandNegative, maximumRange, minimumRange) {
            var minVal = undefined;
            var maxVal = undefined;
            var fromVal = undefined;
            var toVal = undefined;
            var prettifyVal = undefined;
            var onFinishVal = undefined;

            if (strand == '+') {
                minVal = scale.start;
                maxVal = scale.end;
                fromVal = scale.start;
                toVal = scale.end;
                prettifyVal = function (num) {
                    return num;
                };
                onFinishVal = onFinishWhenStrandPositive;
            } else {
                minVal = minimumRange - minimumRange, /*min - min*/
                    maxVal = maximumRange - minimumRange, /*max - min*/
                    fromVal = maximumRange - scale.end, /*max - to*/
                    toVal = maximumRange - scale.start, /*max - from*/
                    prettifyVal = function (num) {
                        return maximumRange - num; /*max - num*/
                    },
                    onFinishVal = onFinishWhenStrandNegative;
            }

            $(name).ionRangeSlider({
                type: "double",
                skin: "square",
                min: minVal,
                max: maxVal,
                from: fromVal,
                to: toVal,
                prettify: prettifyVal,
                drag_interval: true,
                onFinish: onFinishVal
            });
        }
        this.locationScopeChanger.updateProteinlocationScopeChanger = function (name, onFinish, maximumRange) {
            $(name).ionRangeSlider({
                type: "double",
                min: 0,
                max: maximumRange,
                from: 0,
                to: maximumRange,
                drag_interval: true,
                skin: "square",
                onFinish: onFinish
            });
        }

        this.pdfCreator = new Object();
        this.pdfCreator.create = function (gene, idForCanvas) {
            //init attributes
            var doc = new jsPDF();
            var space = 5;
            var width = 90;
            var height = 15;
            var rowHeight = 40;
            var startY = 40;
            var transcriptsPerPage = 6;
            doc.setFontSize(10);

            //introduction text
            doc.text(3 * space, 2 * space, gene.gene_symbol + " " + gene.specieName + ", " + +gene.transcripts.length + " transcripts");
            doc.text(3 * space, 3 * space, "chr" + gene.chromosome + ":" + numberToTextWithCommas(gene.scale.start) + "-" + numberToTextWithCommas(gene.scale.end));

            //drawing each transcript
            for (var i = 0; i < gene.transcripts.length; i++) {
                if (i % transcriptsPerPage == 0) {
                    //adding scale for every new page
                    var canvasScaleGenomic = document.getElementById("canvas-scale" + idForCanvas);
                    var imgGenomicScale = canvasScaleGenomic.toDataURL("image/png");
                    var canvasScaleProtein = document.getElementById("canvas-scale-protein" + idForCanvas);
                    var imgProteinScale = canvasScaleProtein.toDataURL("image/png");

                    doc.addImage(imgGenomicScale, 3 * space, 3 * space, width, height * 1.5);
                    doc.addImage(imgProteinScale, 3 * space + width + space, 3 * space, width, height * 1.5);
                }

                //getting images from canvases
                var canvasGenomic = document.getElementById("canvas-genomic" + idForCanvas + i);
                var imgGenomic = canvasGenomic.toDataURL("image/png");
                var canvasTranscript = document.getElementById("canvas-transcript" + idForCanvas + i);
                var imgTranscript = canvasTranscript.toDataURL("image/png");
                var canvasProtein = document.getElementById("canvas-protein" + idForCanvas + i);
                var imgProtein = canvasProtein.toDataURL("image/png");
                doc.setFontSize(10);
                doc.text(3 * space, startY + rowHeight * (i % transcriptsPerPage), "Transcript: " + gene.transcripts[i].name + " Protein: " + gene.transcripts[i].protein_name);

                //drawing. parameters:x,y,width,height
                doc.addImage(imgGenomic, 3 * space, startY + space + rowHeight * (i % transcriptsPerPage), width, height);
                doc.addImage(imgTranscript, 3 * space + width + space, startY + space + rowHeight * (i % transcriptsPerPage), width, height / 2);
                doc.addImage(imgProtein, 3 * space + width + space, startY + space + rowHeight * (i % transcriptsPerPage) + height, width, height);

                if ((i + 1) % transcriptsPerPage == 0) {
                    //adding new page when finished full page
                    doc.addPage();
                }

            }
            //saving in user computer
            doc.save(gene.gene_symbol + ".pdf");
        }

        this.TranscriptDisplayManager = new Object();
        this.TranscriptDisplayManager.addTranscripts = function (transcripts) {
            this.transcripts = transcripts;
        }
        this.TranscriptDisplayManager.hideTranscriptByIndex = function (index) {
            var transcripts = this.transcripts;
            transcripts[index].genomicView = false;
            transcripts[index].transcriptView = false;
            transcripts[index].proteinView = false;
        };
        this.TranscriptDisplayManager.showTranscript = function (index, viewMode) {
            if (viewMode === "genomic") {
                this.transcripts[index].genomicView = true;
                this.transcripts[index].transcriptView = false;
                this.transcripts[index].proteinView = false;
            } else if (viewMode === "transcript") {
                this.transcripts[index].genomicView = false;
                this.transcripts[index].transcriptView = true;
                this.transcripts[index].proteinView = false;
            } else if (viewMode === "protein") {
                this.transcripts[index].genomicView = false;
                this.transcripts[index].transcriptView = false;
                this.transcripts[index].proteinView = true;
            } else if (viewMode === "all") {
                this.transcripts[index].genomicView = true;
                this.transcripts[index].transcriptView = true;
                this.transcripts[index].proteinView = true;
            } else if (viewMode === "transcript_protein") {
                this.transcripts[index].genomicView = false;
                this.transcripts[index].transcriptView = true;
                this.transcripts[index].proteinView = true;
            }
        };
        this.TranscriptDisplayManager.changeViewMode = function (newViewMode) {
            for (var index = 0; index < this.transcripts.length; index++) {
                if (this.isTranscriptShownByIndex(index)) {
                    this.showTranscript(index, newViewMode)
                }
            }
        };
        this.TranscriptDisplayManager.isTranscriptShownByIndex = function (index) {
            if ((this.transcripts[index].genomicView) ||
                (this.transcripts[index].transcriptView) ||
                (this.transcripts[index].proteinView)) {
                return true;
            }

            return false;
        }
        this.TranscriptDisplayManager.countShownTranscripts = function () {
            var results = new Object();
            var counter = 0;

            for (var i = 0; i < this.transcripts.length; i++) {
                if (this.isTranscriptShownByIndex(i)) {
                    counter = counter + 1;
                }
            }

            results.shownTranscripts = counter;
            results.hiddenTranscripts = this.transcripts.length - counter;
            return results;
        }
    };
}