class Exon {
    constructor(dbExon, geneExons, cdsStart, cdsEnd, numOfExonInTranscript, startCoordinate = 0, proteinStart = 0, cutLength=0) {
        
        this.cutLength=cutLength;
        this.genomicViewStart = dbExon.genomic_start_tx - startCoordinate - 1; //-1  because it is zero based
        this.genomicViewEnd = dbExon.genomic_end_tx - startCoordinate;
        this.transcriptViewStart = dbExon.abs_start_CDS - proteinStart;
        this.transcriptViewEnd = dbExon.abs_end_CDS - proteinStart;
        this.id = dbExon.abs_end;
        this.color = geneExons[dbExon.genomic_start_tx][dbExon.genomic_end_tx].color;
        this.orderInTranscript = dbExon.order_in_transcript;
        this.numOfExonInTranscript = numOfExonInTranscript;

        this.isUTRStart = undefined;
        this.isUTREnd = undefined;
        this.isUTRAll = false;


        //finding utr for later drawings 
        if (dbExon.abs_start_CDS == 0) { //that is the representation is the database
            this.isUTRAll = true;
        } else {
            if (dbExon.genomic_start_tx <= cdsStart && cdsStart <= dbExon.genomic_end_tx) {
                //cds_start in mid exon
                this.isUTRStart = cdsStart - dbExon.genomic_start_tx;
            }
            if (dbExon.genomic_start_tx <= cdsEnd && cdsEnd <= dbExon.genomic_end_tx) {
                //cds_end in mid exon
                this.isUTREnd = dbExon.genomic_end_tx - cdsEnd;
            }
        }

    }
    //draw rectangle, border and text or polygon if not all exon is in cds. note that utrStart and utrEnd are bases in the beginning or end that are out of the cds. if all is out utrAll is true
    drawExonInGenomicView(context, spacing, coordinatesWidth, beginningEmpty, endEmpty, canvasWidth, isStrandNegative, spaceAfterCut) {
        const exonWidth = Math.max(3, (this.genomicViewEnd - this.genomicViewStart + 1) * coordinatesWidth);
        const exonHeight = 70;
        var spaceAfterCut=this.cutLength>0? spaceAfterCut :0;
        var exonX = (this.genomicViewStart - this.cutLength )* coordinatesWidth + beginningEmpty+spaceAfterCut;
        const exonY = spacing - exonHeight / 2;
        var utrLeft = this.isUTRStart;
        var utrRight = this.isUTREnd;
        const utrAll = this.isUTRAll;

        if (isStrandNegative) {
            var exonX = canvasWidth - (this.genomicViewStart - this.cutLength ) * coordinatesWidth - endEmpty - exonWidth -spaceAfterCut;
            var utrLeft = this.isUTREnd;
            var utrRight = this.isUTRStart;
        }

        context.beginPath();
        if (utrLeft == undefined && utrRight == undefined && (!utrAll)) {
            context.rect(exonX, exonY, exonWidth, exonHeight);
        } else if (utrAll) {
            context.rect(exonX, exonY + (exonHeight / 4), exonWidth, exonHeight / 2);
        } else if (utrLeft != undefined && utrRight == undefined) {

            context.moveTo(exonX, exonY + (exonHeight / 4));
            context.lineTo(exonX, exonY + (3 * exonHeight / 4));
            context.lineTo(exonX + utrLeft * coordinatesWidth, exonY + (3 * exonHeight / 4));
            context.lineTo(exonX + utrLeft * coordinatesWidth, exonY + exonHeight);
            context.lineTo(exonX + exonWidth, exonY + exonHeight);
            context.lineTo(exonX + exonWidth, exonY);
            context.lineTo(exonX + utrLeft * coordinatesWidth, exonY);
            context.lineTo(exonX + utrLeft * coordinatesWidth, exonY + (exonHeight / 4));

        } else if (utrLeft == undefined && utrRight != undefined) {

            context.moveTo(exonX, exonY);
            context.lineTo(exonX, exonY + exonHeight);
            context.lineTo(exonX + exonWidth - utrRight * coordinatesWidth, exonY + exonHeight);
            context.lineTo(exonX + exonWidth - utrRight * coordinatesWidth, exonY + (3 * exonHeight / 4));
            context.lineTo(exonX + exonWidth, exonY + (3 * exonHeight / 4));
            context.lineTo(exonX + exonWidth, exonY + (exonHeight / 4));
            context.lineTo(exonX + exonWidth - utrRight * coordinatesWidth, exonY + (exonHeight / 4));
            context.lineTo(exonX + exonWidth - utrRight * coordinatesWidth, exonY);

        } else if (utrLeft != undefined && utrRight != undefined) {
            context.moveTo(exonX, exonY + (exonHeight / 4));
            context.lineTo(exonX, exonY + (3 * exonHeight / 4));
            context.lineTo(exonX + utrLeft * coordinatesWidth, exonY + (3 * exonHeight / 4));
            context.lineTo(exonX + utrLeft * coordinatesWidth, exonY + exonHeight);
            context.lineTo(exonX + utrRight * coordinatesWidth, exonY + exonHeight);
            context.lineTo(exonX + utrRight * coordinatesWidth, exonY + (3 * exonHeight / 4));
            context.lineTo(exonX + exonWidth, exonY + (3 * exonHeight / 4));
            context.lineTo(exonX + exonWidth, exonY + (exonHeight / 4));
            context.lineTo(exonX + utrRight * coordinatesWidth, exonY + (exonHeight / 4));
            context.lineTo(exonX + utrRight * coordinatesWidth, exonY);
            context.lineTo(exonX + utrLeft * coordinatesWidth, exonY);
            context.lineTo(exonX + utrLeft * coordinatesWidth, exonY + (exonHeight / 4));
        }
        context.closePath();
        context.fillStyle = this.color;
        context.fill();
        context.strokeStyle = "grey";
        context.stroke();

    }


    //draw rectangle, border and text
    drawExonInTranscriptView(context, coordinatesWidth, canvasWidth, startHeight) {
        if (this.transcriptViewStart == 0) {
            return;
        }

        var exonWidth = (this.transcriptViewEnd - this.transcriptViewStart + 1) * coordinatesWidth;
        var exonHeight = 25;
        var exonX = this.transcriptViewStart * coordinatesWidth; //currX;
        var exonY = startHeight - exonHeight / 2;
        if (exonX + exonWidth >= canvasWidth) {
            exonWidth = Math.max(1, canvasWidth - exonX - 2);
        }

        //background color
        context.fillStyle = this.color;
        context.fillRect(exonX, exonY, exonWidth, exonHeight);
        //border
        context.strokeStyle = "grey";
        context.strokeRect(exonX, exonY, exonWidth, exonHeight);
    }

    genomicTooltip(startHeight, coordinatesWidth, beginningEmpty, endEmpty, canvasWidth, isStrandNegative) {
        var spaceAfterCut=50;
        const exonWidth = Math.max(3, (this.genomicViewEnd - this.genomicViewStart + 1) * coordinatesWidth);
        const exonHeight = 70;
        var spaceAfterCut=this.cutLength>0? spaceAfterCut :0;
        var exonX = (this.genomicViewStart - this.cutLength )* coordinatesWidth + beginningEmpty+spaceAfterCut;
        const exonY = startHeight - exonHeight / 2;

        if (isStrandNegative) {
            var exonX = canvasWidth - (this.genomicViewStart - this.cutLength ) * coordinatesWidth - endEmpty - exonWidth -spaceAfterCut;
        }
        return [exonX, exonY, exonWidth, exonHeight, "exon: " + this.orderInTranscript + "/" + this.numOfExonInTranscript];

    }

    transcriptTooltip(coordinatesWidth,canvasWidth,startHeight) {
        var exonWidth = (this.transcriptViewEnd - this.transcriptViewStart + 1) * coordinatesWidth;
        var exonHeight = 25;
        var exonX = this.transcriptViewStart * coordinatesWidth;
        var exonY = startHeight - exonHeight / 2;
        if (exonX + exonWidth >= canvasWidth) {
            exonWidth = Math.max(1, canvasWidth - exonX - 2);
        }
        return [exonX, exonY, exonWidth, exonHeight, "exon: " + this.orderInTranscript + "/" + this.numOfExonInTranscript]
    }

}