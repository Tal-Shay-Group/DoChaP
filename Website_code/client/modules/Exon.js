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
        this.length=dbExon.abs_end_CDS-dbExon.abs_start_CDS+1; //in nuc
        this.genomic_start_tx=dbExon.genomic_start_tx;
        this.genomic_end_tx=dbExon.genomic_end_tx;

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
    drawExonInGenomicView(context, startHeight, coordinatesWidth, beginningEmpty, endEmpty, canvasWidth, isStrandNegative, spaceAfterCut) {
        var position=this.genomicViewPosition(coordinatesWidth, startHeight, spaceAfterCut, beginningEmpty, canvasWidth, endEmpty, isStrandNegative);
        
        const exonWidth =position.exonWidth;
        const exonHeight = position.exonHeight;
        var exonX = position.exonX;
        const exonY = position.exonY;
        
        var utrLeft = this.isUTRStart;
        var utrRight = this.isUTREnd;
        const utrAll = this.isUTRAll;

        if (isStrandNegative) {
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

        context.save();
        context.translate(0,0);
        context.shadowColor = "#898";
        context.shadowBlur = 4;
        context.shadowOffsetX = 2;
        context.shadowOffsetY = 3;
        context.fillStyle = this.color;
        context.fill();
        context.restore();
        
        context.strokeStyle = "grey";
        context.stroke();

    }


    //draw rectangle, border and text
    drawExonInTranscriptView(context, coordinatesWidth, canvasWidth, startHeight) {
        //if not in cds so it does not show in *transcript view*
        if (this.transcriptViewStart == 0) {
            return;
        }
        
        //position
        var position=this.transcriptViewPosition(coordinatesWidth, startHeight);
        var exonWidth = position.exonWidth;
        var exonHeight = position.exonHeight;
        var exonX = position.exonX;
        var exonY = position.exonY;
        
        //background color
        context.fillStyle = this.color;
        context.fillRect(exonX, exonY, exonWidth, exonHeight);
        //border
        context.strokeStyle = "grey";
        context.strokeRect(exonX, exonY, exonWidth, exonHeight);
    }

    genomicTooltip(startHeight, coordinatesWidth, beginningEmpty, endEmpty, canvasWidth, isStrandNegative,spaceAfterCut) {
        const position=this.genomicViewPosition(coordinatesWidth, startHeight, spaceAfterCut, beginningEmpty, canvasWidth, endEmpty,isStrandNegative);
        const exonWidth =position.exonWidth;
        const exonHeight = position.exonHeight;
        const exonX = position.exonX;
        const exonY = position.exonY;
        var text="Exon: " + this.orderInTranscript + "/" + this.numOfExonInTranscript+"<br>"+numberToTextWithCommas(this.genomic_start_tx)+" - "+numberToTextWithCommas(this.genomic_end_tx);
        return [exonX, exonY, exonWidth, exonHeight, text,undefined];

    }

    transcriptTooltip(coordinatesWidth,canvasWidth,startHeight) {
        const position=this.transcriptViewPosition(coordinatesWidth, startHeight);
        const exonWidth = position.exonWidth;
        const exonHeight = position.exonHeight;
        const exonX = position.exonX;
        const exonY = position.exonY;
        var text="Exon: " + this.orderInTranscript + "/" + this.numOfExonInTranscript+"<br>Length: "+this.length+"bp/"+(Math.round(this.length/3 * 100) / 100)+"AA";
        return [exonX, exonY, exonWidth, exonHeight, text , undefined]
    }

    transcriptViewPosition(coordinatesWidth, startHeight){
        var pos=new Object();
        pos.exonWidth = (this.transcriptViewEnd - this.transcriptViewStart + 1) * coordinatesWidth;
        pos.exonHeight = 25;
        pos.exonX = this.transcriptViewStart * coordinatesWidth;
        pos.exonY = startHeight - pos.exonHeight / 2;
        
        // if (pos.exonX + pos.exonWidth >= canvasWidth) {
        //     pos.exonWidth = Math.max(1, canvasWidth - pos.exonX - 2);
        // }

        return pos;
    }

    genomicViewPosition(coordinatesWidth, startHeight, spaceAfterCut, beginningEmpty, canvasWidth, endEmpty, isStrandNegative){
        var pos=new Object();
        pos.spaceAfterCut=this.cutLength>0? spaceAfterCut :0;
        pos.exonWidth = Math.max(3, (this.genomicViewEnd - this.genomicViewStart + 1) * coordinatesWidth);
        pos.exonHeight = 70;
        pos.exonX = (this.genomicViewStart - this.cutLength )* coordinatesWidth + beginningEmpty+pos.spaceAfterCut;
        pos.exonY = startHeight - pos.exonHeight / 2;
        
        if(isStrandNegative){
            pos.exonX=canvasWidth - (this.genomicViewStart - this.cutLength ) * coordinatesWidth - endEmpty - pos.exonWidth -pos.spaceAfterCut;
        }

        return pos;
    }
        

}