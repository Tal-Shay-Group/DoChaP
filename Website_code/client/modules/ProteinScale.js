class ProteinScale {

    constructor(length, zoomInStart = 0, zoomInEnd = length) {
        this.length = length;
        this.zoomInStart = zoomInStart; //in nuc
        this.zoomInEnd = zoomInEnd; //in nuc
    }
    /**
     * this scale is for transcript and protein views to understand proportions
     * @param {string} canvasID - name of canvas in controller
     */
    draw(canvasID) {
        //calculations
        var graphicLayout = new ProteinGraphicLayout(canvasID, this);
        var context = graphicLayout.context;
        //clear canvas from before
        context.clearRect(0, 0, graphicLayout.canvasWidth, graphicLayout.canvasHeight);

        //gridlines
        this.drawProteinGridLines(graphicLayout.context, graphicLayout.coordinatesWidth, graphicLayout.startHeight, graphicLayout.lengthOfScale * graphicLayout.coordinatesWidth, graphicLayout.skip, graphicLayout.endEmpty);

        //line graphics
        createBaseLine(context, 0, graphicLayout.startHeight, graphicLayout.lengthOfScale * graphicLayout.coordinatesWidth, graphicLayout.lineThickness);
    }

    /** 
     * this is for the transcript and protein scales. add gridline after constant skip
     * distance calculated and the position.
     */
    drawProteinGridLines(context, coordinatesWidth, startHeight, canvasWidth, skip, endEmpty) {
        var gridLength = 30;
        var lineheight = startHeight - (gridLength - 8) / 2;
        var noNumberZone = -50; //in px (in the end)
        for (var i = -(this.zoomInStart / 3 % skip);
            (i * coordinatesWidth + noNumberZone) < canvasWidth - endEmpty; i = i + skip) {
            context.fillRect(i * coordinatesWidth, lineheight, 1, gridLength);

        }

        //draw number
        context.font = "20px Calibri";
        context.fillText("Nucleotide", 10, 30);
        context.fillText("Amino acid", 10, 125);

        //i is in nuclotides
        for (var i = -(this.zoomInStart / 3 % skip);
            (i * coordinatesWidth) < canvasWidth - endEmpty; i = i + skip) {

            //skips numbers before beginning
            if ((i * coordinatesWidth) < -5) {
                continue;
            }
            //nucloteide number
            context.save();
            context.translate(coordinatesWidth * i + 3, lineheight - 3);
            context.rotate(-Math.PI / 8);
            context.fillStyle = "black"
            context.font = "15px Calibri";
            context.textAlign = "left";
            context.fillText(numberToTextWithCommas(Math.round(i * 3 + this.zoomInStart)), 0, 0);
            context.restore();

            //amino acid number
            context.save();
            context.translate(coordinatesWidth * i, lineheight + 40);
            context.rotate(Math.PI / 8);
            context.fillStyle = "black"
            context.font = "15px Calibri";
            context.textAlign = "left";
            context.fillText(numberToTextWithCommas(Math.round(i + this.zoomInStart / 3)), 0, 0);
            context.restore();
        }
    }

    drawBehind(canvasID) {
        //calculations
        var graphicLayout = new ProteinGraphicLayout(canvasID, this);
        var context = graphicLayout.context;

        //clear all from before
        context.clearRect(0, 0, graphicLayout.canvasWidth, graphicLayout.canvasHeight);

        //actual drawings
        context.fillStyle = "#e1e1e1";
        for (var i = -(this.zoomInStart / 3 % graphicLayout.skip);
            (i * graphicLayout.coordinatesWidth) < graphicLayout.canvasWidth - graphicLayout.endEmpty; i = i + graphicLayout.skip) {
            context.fillRect(i * graphicLayout.coordinatesWidth, 150, 1, graphicLayout.canvasHeight);
        }
    }

}