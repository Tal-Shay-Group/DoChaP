class Transcript {
    /**
     * 
     * @param {Transcript row from db} dbTranscript 
     * @param {Gene} gene the gene of the transcript
     */
    constructor(dbTranscript, gene) {
        //regular db attributes
        this.gene = gene;
        this.id=dbTranscript.transcript_refseq_id!=undefined?dbTranscript.transcript_refseq_id:dbTranscript.transcript_ensembl_id;
        this.transcript_refseq_id=dbTranscript.transcript_refseq_id;
        this.transcript_ensembl_id=dbTranscript.transcript_ensembl_id;
        this.cds_start = dbTranscript.cds_start;
        this.cds_end = dbTranscript.cds_end;
        this.tx_start = dbTranscript.tx_start;
        this.tx_end = dbTranscript.tx_end;
        this.exonCount = dbTranscript.exon_count;
        this.ucsc_id = dbTranscript.ucsc_id;
        this.length = gene.end - gene.start;
        this.maxProteinLength = gene.maxProteinLength;
        this.startCoordinate = gene.start;
        this.transcriptEnsemblLink = this.getEnsemblTranscriptLink(dbTranscript.ensembl_ID, gene.specie);
        this.isStrandNegative = (gene.strand == '-');
        this.name=this.getName(dbTranscript.transcript_refseq_id,dbTranscript.transcript_ensembl_id)

        //protein attributes
        this.proteinId = dbTranscript.protein.protein_refseq_id!=undefined?dbTranscript.protein.protein_refseq_id:dbTranscript.protein.protein_ensembl_id;
        this.protein_refseq_id=dbTranscript.protein.protein_refseq_id;
        this.proteinLength = dbTranscript.protein.length * 3; // in base units
        this.proteinLengthInAA = dbTranscript.protein.length;
        this.description = dbTranscript.protein.description;
        this.proteinSynonyms = dbTranscript.protein.synonyms;
        this.protein_ensembl_id = dbTranscript.protein.protein_ensembl_id;
        // this.proteinUniprotID = dbTranscript.protein.uniprot_id;
        this.proteinEnsemblLink = this.getEnsemblProteinLink(dbTranscript.protein.protein_ensembl_id, gene.specie);
        this.protein_name=this.getName(dbTranscript.protein.protein_refseq_id,dbTranscript.protein.protein_ensembl_id)
        
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
        this.domains = Domain.groupCloseDomains(this.domains);
        this.domains.sort(Domain.compare); //which domain on top of who, in protein view, or who above who in extended view
        // Domain.showNameOfDomains(this.domains); //when commented means showing currently all domains

    }
/**
 * main function to be called when creating canvases or changing zoom in/view settings
 * @param {String} genomicViewCanvasID 
 * @param {String} transcriptViewCanvasID 
 * @param {String} proteinViewCanvasID 
 * @param {String} tooltipManager 
 * @param {String} proteinExtendCanvasID 
 */
    show(genomicViewCanvasID, transcriptViewCanvasID, proteinViewCanvasID, tooltipManager, proteinExtendCanvasID) {
        //if not shown
        if(!(this.genomicView ||this.transcriptView|| this.proteinView)){
            return;
        }

        //draw and everything connected
        this.tooltip(genomicViewCanvasID, transcriptViewCanvasID, proteinViewCanvasID, proteinExtendCanvasID, tooltipManager)
        this.draw(genomicViewCanvasID, transcriptViewCanvasID, proteinViewCanvasID);
        this.drawExtended(proteinExtendCanvasID);
    }

/**
 * create tootltip attachments
 * @param {String} genomicViewCanvasID 
 * @param {String} transcriptViewCanvasID 
 * @param {String} proteinViewCanvasID 
 * @param {String} proteinExtendCanvasID 
 * @param {tooltipManager} tooltipManager where to place tooltip information for further use
 */
    tooltip(genomicViewCanvasID, transcriptViewCanvasID, proteinViewCanvasID, proteinExtendCanvasID, tooltipManager) {
        tooltipManager[genomicViewCanvasID] = this.tooltipGenomicView(genomicViewCanvasID);
        tooltipManager[transcriptViewCanvasID] = this.tooltipTranscriptView(transcriptViewCanvasID);
        tooltipManager[proteinViewCanvasID] = this.tooltipProteinView(proteinViewCanvasID);
        tooltipManager[proteinExtendCanvasID] = this.tooltipProteinExtendView(proteinExtendCanvasID);
        tooltipManager[proteinViewCanvasID + "object"] = this;
       
        //binding to canvas
        $("canvas").unbind();
        $("canvas")
            .mousemove(function (event) {
                var showTextValues = Transcript.showText(event,tooltipManager);
                if (showTextValues[0]) {
                    $("#myTooltip").show();
                    $("#myTooltip").css("top", event.pageY + 5);
                    $("#myTooltip").css("left", event.pageX + 5);
                    $("#myTooltip").html(showTextValues[1]);
                    if (showTextValues[2] == 'click') {
                        $('canvas').css('cursor', 'pointer');
                    }
                } else {
                    $("#myTooltip").hide();
                    $('canvas').css('cursor', 'auto');
                }
            }).mouseleave(function () {
                    // $("#myTooltip").hide();
                    $('canvas').css('cursor', 'auto');
                });
    }
    /**
     *for tooltips- checks if mouse on domain. 
     * @param {event} event 
     * @param {tooltipManager} tooltipManager tooltip information for checking
     */
    static showText(event,tooltipManager){
        var res = [false, ""];
        if (tooltipManager[event.target.id] != undefined) {
            var offset = event.target.getBoundingClientRect();
            var exon = tooltipManager[event.target.id];
            for (var i = 0; i < exon.length; i++) {
                if (event.clientX - offset.left >= exon[i][0] && event.clientX - offset.left <= exon[i][0] + exon[i][2] &&
                    event.clientY - offset.top >= exon[i][1] && event.clientY - offset.top <= exon[i][1] + exon[i][3]) {
                    return [true, exon[i][4], exon[i][5]];
                }
            }
        }
        return res;
    }

    /**
     * genomic tooltips
     * @param {String} genomicViewCanvasID 
     */
    tooltipGenomicView(genomicViewCanvasID) {
        var graphicLayout = new GenomicGraphicLayout(genomicViewCanvasID, this.gene);
        var isStrandNegative = this.isStrandNegative;
        var tooltips = []; //we will fill now

        //for every exons
        for (i = 0; i < this.exons.length; i++) {
            var tooltipData = this.exons[i].genomicTooltip(graphicLayout.startHeight, graphicLayout.coordinatesWidth, graphicLayout.beginningEmpty, graphicLayout.endEmpty, graphicLayout.canvasWidth, isStrandNegative, graphicLayout.spaceAfterCut);
            tooltips.push(tooltipData);
        }

        return tooltips;

    }
    /**
     * 
     * @param {String} transcriptViewCanvasID 
     */
        tooltipTranscriptView(transcriptViewCanvasID) {
        //init attributes
        var canvasE = document.getElementById(transcriptViewCanvasID);
        var canvasHeight = canvasE.height;
        var canvasWidth = canvasE.width;
        var lineThickness = 4;
        var startHeight = (canvasHeight - lineThickness) / 2; //devide by 2 so its the middle
        var coordinatesWidth = ((canvasWidth - 50) / this.shownLength);
        var tooltips = []; //we will fill now
        
        //for every exon
        for (var i = 0; i < this.exons.length; i++) {
            var tooltipData = this.exons[i].transcriptTooltip(coordinatesWidth, startHeight)
            tooltips.push(tooltipData);
        }
        return tooltips;
    }

    /**
     * 
     * @param {String} proteinViewCanvasID 
     */
    tooltipProteinView(proteinViewCanvasID) {
        //init attributes
        var domains = this.domains;
        var startHeight = 25;
        var canvasP = document.getElementById(proteinViewCanvasID);
        var canvasWidth = canvasP.width;
        var coordinatesWidth = ((canvasWidth - 50) / this.shownLength);
        var tooltips = []; //we will fill now

        //for every domain
        for (var i = domains.length - 1; i >= 0; i--) {
            var tooltipData = domains[i].tooltip(coordinatesWidth, startHeight);
            tooltips.push(tooltipData);
        }
        return tooltips;
    }

    /**
     * the fourth view
     * @param {String} proteinExtendViewCanvasID 
     */
    tooltipProteinExtendView(proteinExtendViewCanvasID) {

        //change canvas size (height) to fit number of overlapping domains
        this.changeCanvasSizeForExtendedView(proteinExtendViewCanvasID);

        //init attributes
        var domains = this.domains;
        var startHeight = 25;
        var canvasP = document.getElementById(proteinExtendViewCanvasID);
        var canvasWidth = canvasP.width;
        var coordinatesWidth = ((canvasWidth - 50) / this.shownLength);
        var tooltips = []; //we will fill now

        //for every domain look if it is grouped and add "inner" domains
        for (var i = domains.length - 1; i >= 0; i--) {
            var tooltipArr = domains[i].proteinExtendTooltip(coordinatesWidth, startHeight);

            for (var j = 0; j < tooltipArr.length; j++) {
                tooltips.push(tooltipArr[j]);
            }

        }
        return tooltips;
    }
/**
 * draws all views
 * @param {String} genomicViewCanvasID 
 * @param {String} transcriptViewCanvasID 
 * @param {Strin} proteinViewCanvasID 
 */
    draw(genomicViewCanvasID, transcriptViewCanvasID, proteinViewCanvasID) {
        this.drawGenomicView(genomicViewCanvasID);
        this.drawTranscriptView(transcriptViewCanvasID);
        this.drawProteinView(proteinViewCanvasID);
    }

    /**
     * genomic view consists of line and rectangles with exon order names
     * @param {String} canvasID 
     */
    drawGenomicView(canvasID) {
     
        var graphicLayout = new GenomicGraphicLayout(canvasID, this.gene);
        var strand = this.gene.strand;
        var startCoordinate = this.startCoordinate;
        var context = graphicLayout.context;
        //clear canvas from before
        context.closePath();
        context.clearRect(0, 0, graphicLayout.canvasWidth, graphicLayout.canvasHeight)

        //base line
        createBaseLine(graphicLayout.context, 0, graphicLayout.startHeight, graphicLayout.canvasWidth, graphicLayout.lineThickness);

        //draw cut-off symbol
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

    /**
     * transctipt view consists  exon rectangles filling the canvas in order and proportions
     * @param {String} canvasID 
     */
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
            exons[i].drawExonInTranscriptView(context, coordinatesWidth, startHeight);
        }
    }

    /**
     * protein view consists of a line and currently circles in color of exons they are made of in gradient manner
     * @param {String} canvasID 
     */
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

    /**
     * calculating ensemble transcript link
     * @param {String} ensembl_id 
     * @param {String} specie species name in db
     */
    getEnsemblTranscriptLink(ensembl_id, specie) {
        return "https://www.ensembl.org/" + Species.ensembleSpecieName(specie) + "/Transcript/Summary?db=core;t=" + ensembl_id;
    }

    /**
     * calculating ensemble protein link
     * @param {String} ensembl_id 
     * @param {String} specie 
     */
    getEnsemblProteinLink(ensembl_id, specie) {
        return "https://www.ensembl.org/" + Species.ensembleSpecieName(specie) + "/Transcript/ProteinSummary?db=core;p=" + ensembl_id;
    }

    /**
     * draw one gridline  inside genomic view- currently not in use
     * @param {canvasContext} context  context to draw on
     * @param {int} x position for gridline
     * @param {int} y position for gridline
     */
    drawGridLine(context, x, y) {
        var gridLength = 10;
        context.fillStyle = "#bfbfbf";
        //draw line
        context.fillRect(x, y - gridLength, 1, gridLength);
    }

    /**
     * compare between two transcriptss, order by size (commented is showing nm before xm)
     * @param {Transcript} a first of two transcripts 
     * @param {Transcript} b second of two transcripts
     */
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

    /**
     * the fourth view (showing overlapping domains next to each other)
     * @param {String} canvasID the canvas already changed to fit the size of domains (its dynammically have changed)
     */
    drawExtended(canvasID) {

       
        //calculations
        var exons = this.exons;
        var canvas = document.getElementById(canvasID);
        var context = canvas.getContext("2d");
        var canvasHeight = canvas.height;
        var canvasWidth = canvas.width;
        var startHeight = 25;
        var domainsInProtein = this.domains;
        var coordinatesWidth = ((canvasWidth - 50) / this.shownLength);
        var heightOfDomainList=canvasHeight;

        //clear old drawings
        context.closePath();
        context.beginPath();
        context.clearRect(0, 0, canvasWidth, canvasHeight);
        context.closePath();

        //actual drawings
        for (var i = 0; i < domainsInProtein.length; i++) {
            domainsInProtein[i].drawExtend(context, coordinatesWidth, startHeight, true, exons,heightOfDomainList);
        }
    }

    /**
     * gets name that includes one or both ID names depends on what exists
     * @param {String} refseq_id 
     * @param {String} ensembl_id 
     */
    getName(refseq_id,ensembl_id){
        if(refseq_id!=undefined && ensembl_id==undefined){
            return refseq_id;
        }
        if(refseq_id==undefined && ensembl_id!=undefined){
            return ensembl_id
        }
        if(refseq_id!=undefined && ensembl_id!=undefined){
            return refseq_id+" / "+ensembl_id;
        }
        return undefined;
    }

    changeCanvasSizeForExtendedView(canvasID){
        var domainsInProtein = this.domains;
        var maxOverlaps=0;
        var domainHeight=25;//in pixel
        var startHeight=25;

        for(var i=0; i<domainsInProtein.length;i++){
            if(domainsInProtein[i].domains!=undefined && domainsInProtein[i].domains.length>maxOverlaps){
                maxOverlaps=domainsInProtein[i].domains.length;
            }
        }
        if(maxOverlaps==0){
            return;
        }
        var canvas = document.getElementById(canvasID);
        canvas.height=domainHeight*maxOverlaps+startHeight;
        canvas.style.height = (domainHeight*maxOverlaps+startHeight)+'px';

    }

}