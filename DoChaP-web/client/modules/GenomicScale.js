class GenomicScale {
    /**
     * 
     * @param {Gene} gene the gene we searched
     */
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
     * @param {String} canvasID canvas id in html
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
        // var skip = getSkipSize(coordinatesWidth);
        // var strand = this.strand;
        
        var graphicLayout = new GenomicGraphicLayout(canvasID, this.gene);
        var strand = this.gene.strand;
        var context = graphicLayout.context;
        var lineThickness = 8;
        var startHeight = 70; //px from top


        //clear all from before
        context.clearRect(0, 0, graphicLayout.canvasWidth, graphicLayout.canvasHeight);

        //line graphics
        createBaseLine(context, 0, startHeight, graphicLayout.canvasWidth, lineThickness);

        //calculate gridlines
        var Xcoordinates = this.gridCoordinates(this.start, graphicLayout.skip, graphicLayout.coordinatesWidth, graphicLayout.canvasWidth, graphicLayout.beginningEmpty, graphicLayout.endEmpty, strand, this.gene.cutOffStart, this.gene.cutOffLength, this.spaceAfterCut);

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
            context.rect(cutX + 4, startHeight - 15 + lineThickness / 2, this.spaceAfterCut - 8, 30);
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
     * @param {canvasContext} context context to draw on
     * @param {String} strand '+' or '-' depends on gene location
     * @param {int} arrowLength wanted size for arrow
     * @param {int} width x coordinate for start point of the arrow
     * @param {int} height y coordinate for start point of the arrow
     */
    drawArrow(context, strand, arrowLength, width, height) { 
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

    /**
     * drawing one gridline (shnata in Herew)
     * @param {canvasContext} context context to draw on
     * @param {int} x location for the gridline
     * @param {int} y start height for gridline
     * @param {String} text the number in text to write above gridline
     * @param {int} canvasWidth 
     * @param {int} beginningEmpty space in the left where it is empty before first exon
     * @param {double} coordinatesWidth the measure of scaling used
     */
    drawGridLine(context, x, y, text, canvasWidth, beginningEmpty, coordinatesWidth) {
        //options
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

/**
 * drawing the gridlines that are behind the views
 * @param {*} canvasID 
 */
    drawBehind(canvasID) {
        //calculating locations
        var graphicLayout = new GenomicGraphicLayout(canvasID, this.gene);
        var strand = this.gene.strand;
        var context = graphicLayout.context;

        //clear all from before
        context.clearRect(0, 0, graphicLayout.canvasWidth, graphicLayout.canvasHeight);

        //calculate gridlines
        var Xcoordinates = this.gridCoordinates(this.start, graphicLayout.skip, graphicLayout.coordinatesWidth, graphicLayout.canvasWidth, graphicLayout.beginningEmpty, graphicLayout.endEmpty, strand, this.gene.cutOffStart, this.gene.cutOffLength, this.spaceAfterCut);

        //draw gridlines
        context.fillStyle = "#e1e1e1";
        for (var i = 0; i < Xcoordinates.length; i++) {
            //draw line
            context.fillRect(Xcoordinates[i].x, 150, 1, graphicLayout.canvasHeight);
        }
    }

    /**
     * we may not write the numbers for gridlines if the are close to start or end 
     * this function makes sure it is located in a good placement to write
     * @param {double} x location where the text is wanted
     * @param {int} beginningEmpty the space in the right where all exon end before it, in pixel units
     * @param {int} emptyFromTextInTheEnd the length in the end where we do not write, pixel units
     * @param {double} coordinatesWidth the measure of scaling used
     */
    isNotCloseToCut(x, beginningEmpty, emptyFromTextInTheEnd, coordinatesWidth) {
        if (this.gene.cutOffStart == -1) {
            return true;
        }

        //text too close to the *left* of the cut
        var cutStartX = (this.gene.cutOffStart - this.start) * coordinatesWidth + beginningEmpty;
        if (cutStartX - x < emptyFromTextInTheEnd && cutStartX - x > 0) {
            return false;
        } else if (cutStartX - x > -55 && cutStartX - x < 0) {
            return false;
        }

        return true;
    }

/**
 * list of grid coordinates and locations
 * @param {int} start first coordinate that shows. from this point we will start the gridlines
 * @param {int} skip skip in nuc
 * @param {double} coordinatesWidth the measure of scaling used
 * @param {int} canvasWidth 
 * @param {int} beginningEmpty space in the left before the first exon
 * @param {int} endEmpty space in the right after the last exon
 * @param {String} strand '+' or '-' depends on the gene
 * @param {int} cutOffStart if exists cut it is the coordinate of start intron (for visual reasons), otherwise -1 
 * @param {int} cutOffLength if exists cut it is the length where we cut intron (for visual reasons), otherwise -1 
 * @param {int} spaceAfterCut if exists it is the size of animation of cut, otherwise 0
 */
    gridCoordinates(start, skip, coordinatesWidth, canvasWidth, beginningEmpty, endEmpty, strand, cutOffStart, cutOffLength, spaceAfterCut) {
        //calculate variables
        var Xcoordinates = [];
        var geneCoordinate = start - (start % skip) + skip;
        var secondCoordinate = skip - (start % skip); //the length till the next rounded after start
        var needCut = (cutOffStart != -1 && cutOffLength != -1); // checks if we need cut
        var hasSpaceOfSkip=false;

        //go through each skip and add gridline to list
        for (var i = secondCoordinate;
            (i * coordinatesWidth) + 2 < canvasWidth; i = i + skip) {
            
            //if there is a cut now we do the cut - there can only be one
            if (needCut && geneCoordinate > cutOffStart) {
                needCut = false;
                hasSpaceOfSkip=true;
                var afterCut = cutOffStart + cutOffLength;
                geneCoordinate = afterCut - (afterCut % skip) + skip
                i = i + spaceAfterCut/coordinatesWidth  - (afterCut % skip) + skip; //so the line is where the after *skip* is also applied and *cut* is applied
            }

            //init new gridline with information
            var grid = new Object();
            grid.text = numberToTextWithCommas(geneCoordinate);
            
            //calculate coordinate x depends on strand
            if (strand == '+') {
                grid.x = (i * coordinatesWidth) + beginningEmpty;
            // } else if (strand == '-' && hasSpaceOfSkip) {
            //     grid.x = canvasWidth - endEmpty - (i * coordinatesWidth) -hasSpaceOfSkip;
            } else if (strand == '-') {
                grid.x = canvasWidth - endEmpty - (i * coordinatesWidth)
            }

            //add new gridline to list
            Xcoordinates.push(grid);
            
            //update new current coordinate
            geneCoordinate = geneCoordinate + skip;
        }
        return Xcoordinates
    }

}