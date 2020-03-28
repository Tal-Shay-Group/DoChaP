class GenomicScale {
    constructor(gene) {
        this.start = gene.start; //lowest coordinate
        this.end = gene.end; //highest coordinate
        this.strand = gene.strand;
        this.chromosomeName = gene.chromosomeName;
        this.gene = gene;
        this.spaceAfterCut = 50; //in pixels
    }

    /**
     * scale is needed for understanding proportions 
     */
    draw(canvasID) {
        //calculations
        // var canvas = document.getElementById(canvasID);
        // var context = canvas.getContext("2d");
        // var canvasHeight = canvas.height;
        // var canvasWidth = canvas.width;
        // var lengthOfScale = this.end - this.start; //both in noclutides
        // var beginningEmpty = 10; //in pixels
        // var endEmpty = 5; //in pixels
        // var coordinatesWidth = (canvas.width - beginningEmpty - endEmpty) / lengthOfScale;
        // if (this.gene.cutOffStart != -1 && this.gene.cutOffLength != -1) {
        //     coordinatesWidth = (canvas.width - beginningEmpty - endEmpty - this.spaceAfterCut) / (lengthOfScale - this.gene.cutOffLength);
        // }
        // var skip = getSkipSize(lengthOfScale, coordinatesWidth);
        // var strand = this.strand;

        var graphicLayout=new GenomicGraphicLayout(canvasID,this.gene);
        var strand= this.gene.strand;
        var context=graphicLayout.context;
        var lineThickness = 8;
        var startHeight = 70; //px from top


        //clear all from before
        context.clearRect(0, 0, graphicLayout.canvasWidth, graphicLayout.canvasHeight);

        //line graphics
        createBaseLine(context, 0, startHeight, graphicLayout.canvasWidth, lineThickness);

        //calculate gridlines
        var Xcoordinates = gridCoordinates(this.start, graphicLayout.skip, graphicLayout.coordinatesWidth, graphicLayout.canvasWidth, graphicLayout.beginningEmpty, graphicLayout.endEmpty, strand, this.gene.cutOffStart, this.gene.cutOffLength, this.spaceAfterCut);


        //draw gridlines
        for (var i = 0; i < Xcoordinates.length; i++) {
            this.drawGridLine(context, Xcoordinates[i].x, startHeight, Xcoordinates[i].text, graphicLayout.canvasWidth, graphicLayout.beginningEmpty, graphicLayout.coordinatesWidth)
        }
        //====draw gridlines from before====
        // createGridLines(context, beginningEmpty, coordinatesWidth, startHeight, canvasWidth, lengthOfScale, this.start, false, canvasHeight);
        // this.createNumberLabelsForScale(context, lengthOfScale, skip, coordinatesWidth, beginningEmpty, startHeight, this.start);

        //draw skip explanation
        if (this.gene.cutOffStart != -1 && this.gene.cutOffLength != -1) {
            var cutX = graphicLayout.cutX;
            context.beginPath();
            context.fillStyle = "white";
            context.rect(cutX + 4, startHeight - 15 +lineThickness / 2, this.spaceAfterCut - 8, 30);
            context.fill();
            context.closePath();
            context.beginPath();
            context.fillStyle = "black";
            context.rect(cutX + 4, startHeight - 15 + lineThickness / 2, 1, 30);
            context.fill();
            context.closePath();
            context.beginPath();
            context.fillStyle = "black";
            context.rect(cutX + this.spaceAfterCut - 4, startHeight - 15 + lineThickness / 2, 1, 30);
            context.fill();
            context.closePath();
            context.font = "60px Calibri";
            context.fillStyle = "black";
            context.textAlign = "left";
            context.fillText("...", cutX + 2, startHeight + lineThickness / 2);

        }

        //draw arrow 
        this.drawArrow(context, strand, 100, (graphicLayout.canvasWidth - 100) / 2, 105);
    }



    /** 
     * drawing the arrow for strand
     */
    drawArrow(context, strand, arrowLength, width, height) { //width and height in which the arrow starts
        var arrowWidthLine = 8;
        context.fillStyle = "black";
        //baseline
        context.beginPath();
        context.moveTo(width, height);
        context.lineTo(width + arrowLength, height);
        context.closePath();
        context.stroke();
        //arrow
        if (strand == '+') {
            context.beginPath();
            context.moveTo(width + arrowLength - arrowWidthLine, height - arrowWidthLine);
            context.lineTo(width + arrowLength, height);
            context.lineTo(width + arrowLength - arrowWidthLine, height + arrowWidthLine);
            context.closePath();
            context.fill();
        } else if (strand == '-') {
            context.beginPath();
            context.moveTo(width + arrowWidthLine, height - arrowWidthLine);
            context.lineTo(width, height);
            context.lineTo(width + arrowWidthLine, height + arrowWidthLine);
            context.closePath();
            context.fill();
        }
        context.font = "20px Calibri";
        context.textAlign = "center";
        context.fillText("strand " + strand, width + (arrowLength / 2), height - 5);
    }

    //currently not in use?
    gridCoordinates(skip, coordinatesWidth, canvasWidth, beginningEmpty, endEmpty, strand) {
        var Xcoordinates = [];
        var geneCoordinate = this.start - (this.start % skip) + skip;
        var secondCoordinate = skip - (this.start % skip); //the length till the next rounded after start
        for (var i = secondCoordinate;
            (i * coordinatesWidth) + 2 < canvasWidth; i = i + skip) {
            var grid = new Object();
            grid.text = numberToTextWithCommas(geneCoordinate);
            if (strand == '+') {
                grid.x = (i * coordinatesWidth) + beginningEmpty;
            } else if (strand == '-') {
                grid.x = canvasWidth - endEmpty - (i * coordinatesWidth)
            }
            Xcoordinates.push(grid);
            geneCoordinate = geneCoordinate + skip;
        }
        return Xcoordinates
    }

    // negativeStrandGridCoordinats(skip, coordinatesWidth, canvasWidth, endEmpty){
    //     var Xcoordinates = [];
    //     var geneCoordinate = this.start - (this.start % skip) + skip;
    //     var secondCoordinate = skip - (this.start % skip); //the length till the next rounded after start
    //     for (var i = secondCoordinate;
    //         (i * coordinatesWidth) + 2 < canvasWidth; i = i + skip) {
    //         Xcoordinates.push({
    //             'x': canvasWidth -endEmpty -(i * coordinatesWidth),
    //             'text': numberToTextWithCommas(geneCoordinate)
    //         });
    //         geneCoordinate = geneCoordinate + skip;
    //     }
    //     return Xcoordinates
    // }

    drawGridLine(context, x, y, text, canvasWidth, beginningEmpty, coordinatesWidth) {
        var gridLength = 5;
        var emptyFromTextInTheEnd = 50;
        context.fillStyle = "black";
        context.font = "15px Calibri";
        context.textAlign = "left";

        //draw line
        context.fillRect(x, y - gridLength, 1, gridLength);

        //if needed write text
        if (canvasWidth - x > emptyFromTextInTheEnd && x > 5 && this.isNotCloseToCut(x, beginningEmpty, emptyFromTextInTheEnd, coordinatesWidth)) {
            context.save();
            context.translate(x, y - 8);
            context.rotate(-Math.PI / 8);
            context.fillText(text, 0, 0);
            context.restore();
        }
    }


    drawBehind(canvasID) {
        //calculations
        var canvas = document.getElementById(canvasID);
        var context = canvas.getContext("2d");
        var canvasHeight = canvas.height;
        var canvasWidth = canvas.width;
        var lineThickness = 8;
        var startHeight = 70; //px from top
        var lengthOfScale = this.end - this.start; //both in noclutides
        var beginningEmpty = 10; //in pixels
        var endEmpty = 5; //in pixels
        var coordinatesWidth = (canvas.width - beginningEmpty - endEmpty) / lengthOfScale;
        var skip = getSkipSize(lengthOfScale, coordinatesWidth);
        var strand = this.strand;

        //clear all from before
        context.clearRect(0, 0, canvasWidth, canvasHeight);

        //calculate gridlines
        var Xcoordinates = gridCoordinates(this.start, skip, coordinatesWidth, canvasWidth, beginningEmpty, endEmpty, strand);

        //draw gridlines
        context.fillStyle = "#e1e1e1";
        for (var i = 0; i < Xcoordinates.length; i++) {
            //draw line
            context.fillRect(Xcoordinates[i].x, 200, 1, canvasHeight);
        }
    }

    isNotCloseToCut(x, beginningEmpty, emptyFromTextInTheEnd, coordinatesWidth) {
        if (this.gene.cutOffStart == -1) {
            return true;
        }

        //text too close to the *left* of the cut
        var cutStartX = (this.gene.cutOffStart - this.start) * coordinatesWidth + beginningEmpty;
        if (cutStartX - x < emptyFromTextInTheEnd && cutStartX - x > 0) {
            return false;
        }
        else if (cutStartX - x > -55 && cutStartX - x < 0) {
            return false;
        }

        return true;
    }

}