class Transcript {
    constructor(dbTranscript, gene) {

        //regular db attributes
        this.gene = gene;
        this.id = dbTranscript.transcript_id;
        this.cds_start = dbTranscript.cds_start;
        this.cds_end = dbTranscript.cds_end;
        this.tx_start = dbTranscript.tx_start;
        this.tx_end = dbTranscript.tx_end;
        this.exonCount = dbTranscript.exon_count;
        this.ucsc_id = dbTranscript.ucsc_id;
        this.ensembl_id = dbTranscript.ensembl_ID;
        this.length = gene.end - gene.start;
        this.maxProteinLength = gene.maxProteinLength;
        this.startCoordinate = gene.start;
        this.transcriptEnsemblLink = this.getEnsemblTranscriptLink(dbTranscript.ensembl_ID, gene.specie);
        this.isStrandNegative = (gene.strand == '-');

        //protein attributes
        this.proteinId = dbTranscript.protein.protein_id;
        this.proteinLength = dbTranscript.protein.length * 3; // in base units
        this.proteinLengthInAA = dbTranscript.protein.length;
        this.description = dbTranscript.protein.description;
        this.proteinSynonyms = dbTranscript.protein.synonyms;
        this.proteinEnsemblID = dbTranscript.protein.ensembl_id;
        this.proteinUniprotID = dbTranscript.protein.uniprot_id;
        this.proteinEnsemblLink = this.getEnsemblProteinLink(dbTranscript.protein.ensembl_id, gene.specie);

        // show or hide mode attributes
        this.genomicView = true;
        this.transcriptView = true;
        this.proteinView = true;
        this.proteinExtendView = false;


        //zoom in or out in canvas attributes
        this.shownLength = gene.proteinEnd - gene.proteinStart;
        this.proteinStart = gene.proteinStart;

        //create exons for this transcript
        this.exons = [];
        for (var i = 0; i < dbTranscript.transcriptExons.length; i++) {
            var cutLength = 0;
            if (gene.cutOffStart != -1 && gene.cutOffLength != -1 && dbTranscript.transcriptExons[i].genomic_start_tx >= gene.cutOffStart) {
                cutLength = gene.cutOffLength;
            }
            this.exons[i] = new Exon(dbTranscript.transcriptExons[i], gene.geneExons, this.cds_start, this.cds_end, dbTranscript.transcriptExons.length, gene.start, gene.proteinStart, cutLength);
        }

        //create domains for this transcript
        this.domains = [];
        for (var i = 0; i < dbTranscript.domains.length; i++) {
            this.domains[i] = new Domain(dbTranscript.domains[i], gene.proteinStart);
        }

        //domain sorts and attribute edits
        Domain.findOverlaps(this.domains);
       this.domains=Domain.groupDomains(this.domains);
        this.domains.sort(Domain.compare); //so it is drawn in right order
        Domain.showNameOfDomains(this.domains);

    }

    show(genomicViewCanvasID, transcriptViewCanvasID, proteinViewCanvasID, tooltipManager,proteinExtendCanvasID) {
        this.tooltip(genomicViewCanvasID, transcriptViewCanvasID, proteinViewCanvasID,proteinExtendCanvasID, tooltipManager)
        this.draw(genomicViewCanvasID, transcriptViewCanvasID, proteinViewCanvasID);
        this.drawExtended(proteinExtendCanvasID);
    }

    tooltip(genomicViewCanvasID, transcriptViewCanvasID, proteinViewCanvasID,proteinExtendCanvasID, tooltipManager) {
        tooltipManager[genomicViewCanvasID] = this.tooltipGenomicView(genomicViewCanvasID);
        tooltipManager[transcriptViewCanvasID] = this.tooltipTranscriptView(transcriptViewCanvasID);
        tooltipManager[proteinViewCanvasID] = this.tooltipProteinView(proteinViewCanvasID);
        tooltipManager[proteinExtendCanvasID] = this.tooltipProteinExtendView(proteinExtendCanvasID);
        tooltipManager[proteinViewCanvasID+"object"] = this;

    }

    tooltipGenomicView(genomicViewCanvasID) {
        var graphicLayout = new GenomicGraphicLayout(genomicViewCanvasID, this.gene);
        var isStrandNegative = this.isStrandNegative;
        var tooltips = []; //we will fill now

        for (i = 0; i < this.exons.length; i++) {
            var tooltipData = this.exons[i].genomicTooltip(graphicLayout.startHeight, graphicLayout.coordinatesWidth, graphicLayout.beginningEmpty, graphicLayout.endEmpty, graphicLayout.canvasWidth, isStrandNegative, graphicLayout.canvasWidth,graphicLayout.spaceAfterCut)
            tooltips.push(tooltipData);
        }

        return tooltips;

    }

    tooltipTranscriptView(transcriptViewCanvasID) {
        var canvasE = document.getElementById(transcriptViewCanvasID);
        var canvasHeight = canvasE.height;
        var canvasWidth = canvasE.width;
        var lineThickness = 4;
        var startHeight = (canvasHeight - lineThickness) / 2; //devide by 2 so its the middle
        var coordinatesWidth = ((canvasWidth - 50) / this.shownLength);
        var tooltips = []; //we will fill now

        for (var i = 0; i < this.exons.length; i++) {
            var tooltipData = this.exons[i].transcriptTooltip(coordinatesWidth, canvasWidth, startHeight)
            tooltips.push(tooltipData);
        }
        return tooltips;
    }

    tooltipProteinView(proteinViewCanvasID) {
        var domains = this.domains;
        var startHeight = 25;
        var canvasP = document.getElementById(proteinViewCanvasID);
        var canvasWidth = canvasP.width;
        var coordinatesWidth = ((canvasWidth - 50) / this.shownLength);
        var tooltips = []; //we will fill now

        for (var i = domains.length - 1; i >= 0; i--) {
            var tooltipData = domains[i].tooltip(coordinatesWidth, startHeight);
            tooltips.push(tooltipData);
        }
        return tooltips;
    }

    tooltipProteinExtendView(proteinExtendViewCanvasID) {
        var domains = this.domains;
        var startHeight = 25;
        var canvasP = document.getElementById(proteinExtendViewCanvasID);
        var canvasWidth = canvasP.width;
        var coordinatesWidth = ((canvasWidth - 50) / this.shownLength);
        var tooltips = []; //we will fill now

        for (var i = domains.length - 1; i >= 0; i--) {
            var tooltipArr = domains[i].proteinExtendTooltip(coordinatesWidth, startHeight);
            
            for(var j=0;j<tooltipArr.length; j++){
                tooltips.push(tooltipArr[j]);
            }
            
        }
        return tooltips;
    }

    draw(genomicViewCanvasID, transcriptViewCanvasID, proteinViewCanvasID) {
        this.drawGenomicView(genomicViewCanvasID);
        this.drawTranscriptView(transcriptViewCanvasID);
        this.drawProteinView(proteinViewCanvasID);
    }

    // genomic view consists of line and rectangles with exon order names
    drawGenomicView(canvasID) {
        //calculations
        // var canvas = document.getElementById(canvasID);
        // var context = canvas.getContext("2d");
        // var canvasHeight = canvas.height;
        // var canvasWidth = canvas.width;
        // var lineThickness = 2;
        // var startHeight = 50;
        // var lengthOfGene = this.length;
        // var beginningEmpty = 10; //in pixels
        // var endEmpty = 5; //in pixels
        // var spaceAfterCut = 50;
        // var coordinatesWidth = (canvas.width - beginningEmpty - endEmpty) / lengthOfGene;

        // //if cut exists
        // if(this.gene.cutOffStart != -1 && this.gene.cutOffLength!=-1){
        //     coordinatesWidth = (canvas.width - beginningEmpty - endEmpty - spaceAfterCut) / (lengthOfGene-this.gene.cutOffLength);
        // }

        // var skip = getSkipSize(lengthOfGene, coordinatesWidth);
        var graphicLayout = new GenomicGraphicLayout(canvasID, this.gene);
        var strand = this.gene.strand;
        var startCoordinate = this.startCoordinate;
        var context = graphicLayout.context;
        //clear canvas from before
        context.closePath();
        context.clearRect(0, 0, graphicLayout.canvasWidth, graphicLayout.canvasHeight)

        //gridlines


        // createGridLines(context, beginningEmpty, coordinatesWidth, canvasHeight, canvasWidth, lengthOfGene, startCoordinate, true, startHeight);

        var Xcoordinates = gridCoordinates(startCoordinate, graphicLayout.skip, graphicLayout.coordinatesWidth, graphicLayout.canvasWidth, graphicLayout.beginningEmpty, graphicLayout.endEmpty, strand, this.gene.cutOffStart, this.gene.cutOffLength, graphicLayout.spaceAfterCut);
        for (var i = 0; i < Xcoordinates.length; i++) {
            this.drawGridLine(graphicLayout.context, Xcoordinates[i].x, graphicLayout.startHeight)
        }

        //base line
        createBaseLine(graphicLayout.context, 0, graphicLayout.startHeight, graphicLayout.canvasWidth, graphicLayout.lineThickness);

        //draw skip explanation
        if (this.gene.cutOffStart != -1 && this.gene.cutOffLength != -1) {
            var cutX = graphicLayout.cutX;
            context.beginPath();
            context.fillStyle = "white";
            context.rect(cutX + 4, 0, graphicLayout.spaceAfterCut - 8, 100);
            context.fill();
            context.closePath();
            context.beginPath();
            context.fillStyle = "black";
            context.rect(cutX + 4, graphicLayout.startHeight - 15 + graphicLayout.lineThickness / 2, 1, 30);
            context.fill();
            context.closePath();
            context.beginPath();
            context.fillStyle = "black";
            context.rect(cutX + graphicLayout.spaceAfterCut - 4, graphicLayout.startHeight - 15 + graphicLayout.lineThickness / 2, 1, 30);
            context.fill();
            context.closePath();
            context.font = "60px Calibri";
            context.fillStyle = "black";
            context.fillText("...", cutX + 2, graphicLayout.startHeight + graphicLayout.lineThickness / 2);

        }

        //exon graphics
        for (var i = 0; i < this.exons.length; i++) {
            this.exons[i].drawExonInGenomicView(graphicLayout.context, graphicLayout.startHeight, graphicLayout.coordinatesWidth, graphicLayout.beginningEmpty, graphicLayout.endEmpty, graphicLayout.canvasWidth, this.isStrandNegative, graphicLayout.spaceAfterCut);
        }



    }

    // transctipt view consists  exon rectangles filling the canvas in order and proportions
    drawTranscriptView(canvasID) {
        //calculations
        var exons = this.exons;
        var canvas = document.getElementById(canvasID);
        var context = canvas.getContext("2d");
        var canvasHeight = canvas.height;
        var canvasWidth = canvas.width;
        var lineThickness = 4;
        var startHeight = (canvasHeight - lineThickness) / 2; //devide by 2 so its the middle
        var coordinatesWidth = ((canvasWidth - 50) / this.shownLength);

        //clear canvas from before
        context.clearRect(0, 0, canvasWidth, canvasHeight);

        //exon drawing
        for (var i = 0; i < exons.length; i++) {
            exons[i].drawExonInTranscriptView(context, coordinatesWidth, canvasWidth, startHeight);
        }
    }


    //protein view consists of a line and currently circles in color of exons they are made of in gradient manner
    drawProteinView(canvasID) {
        //calculations
        var exons = this.exons;
        var canvas = document.getElementById(canvasID);
        var context = canvas.getContext("2d");
        var canvasHeight = canvas.height;
        var canvasWidth = canvas.width;
        var proteinLength = this.proteinLength;
        var lineThickness = 4;
        var startHeight = 25;
        var domainsInProtein = this.domains;
        var coordinatesWidth = ((canvasWidth - 50) / this.shownLength);

        //clear old drawings
        context.closePath();
        context.beginPath();
        context.clearRect(0, 0, canvasWidth, canvasHeight);
        context.closePath();

        //draw line
        var proteinEndInView = (proteinLength - this.proteinStart) * coordinatesWidth;
        createBaseLine(context, 0, startHeight, proteinEndInView, lineThickness);

        //white background behind domains so if it transparent the black line won't show behind it
        for (var i = 0; i < domainsInProtein.length; i++) {
            domainsInProtein[i].draw(context, coordinatesWidth, startHeight, false, exons);
        }

        //actual drawings
        for (var i = 0; i < domainsInProtein.length; i++) {
            domainsInProtein[i].draw(context, coordinatesWidth, startHeight, true, exons);
        }
    }

    //calculating ensemble transcript link
    getEnsemblTranscriptLink(ensembl_id, specie) {
        return "https://www.ensembl.org/" + ensembleSpecieName(specie) + "/Transcript/Summary?db=core;t=" + ensembl_id;
    }

    //calculating ensemble protein link
    getEnsemblProteinLink(ensembl_id, specie) {
        return "https://www.ensembl.org/" + ensembleSpecieName(specie) + "/Transcript/ProteinSummary?db=core;p=" + ensembl_id;
    }

    drawGridLine(context, x, y) {
        var gridLength = 10;
        context.fillStyle = "#bfbfbf";
        //draw line
        context.fillRect(x, y - gridLength, 1, gridLength);
    }

    //compare between two transcriptss
    //task: showing by size (commented is showing nm before xm)
    static compare(a, b) {
        /*if ( a.id.substring(0,2) < b.id.substring(0,2) ){
          return -1;
        }
        if ( a.id.substring(0,2) > b.id.substring(0,2) ){
          return 1;
        }*/
        if (a.proteinLength < b.proteinLength) {
            return 1;
        }
        if (a.proteinLength > b.proteinLength) {
            return -1;
        }
        return 0;
    }

    drawExtended(canvasID){
        //calculations
        var exons = this.exons;
        var canvas = document.getElementById(canvasID);
        var context = canvas.getContext("2d");
        var canvasHeight = canvas.height;
        var canvasWidth = canvas.width;
        var proteinLength = this.proteinLength;
        var lineThickness = 4;
        var startHeight = 25;
        var domainsInProtein = this.domains;
        var coordinatesWidth = ((canvasWidth - 50) / this.shownLength);

        //clear old drawings
        context.closePath();
        context.beginPath();
        context.clearRect(0, 0, canvasWidth, canvasHeight);
        context.closePath();

        //actual drawings
        for (var i = 0; i < domainsInProtein.length; i++) {
            domainsInProtein[i].drawExtend(context, coordinatesWidth, startHeight, true, exons);
        }
    }

}