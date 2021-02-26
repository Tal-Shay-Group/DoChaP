class PdfCreator {
    constructor() {}

    create(gene, idForCanvas) {
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
}