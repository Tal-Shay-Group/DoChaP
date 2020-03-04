class ProteinScale {
    
    constructor(length,zoomInStart=0,zoomInEnd=length) {
        this.length=length;
        this.zoomInStart=zoomInStart; //in nuc
        this.zoomInEnd=zoomInEnd; //in nuc
    }
/**
 * this scale is for transcript and protein views to understand proportions
 * @param {string} canvasID - name of canvas in controller
 */
    draw(canvasID) {
        //calculations
        var canvas = document.getElementById(canvasID);
        var context = canvas.getContext("2d");
        var canvasHeight = canvas.height;
        var canvasWidth = canvas.width;
        var lineThickness = 8;
        var startHeight = 70; //space from top
        var lengthOfScale = (this.zoomInEnd-this.zoomInStart)/3; //both in necluotides
        var endEmpty = 50; //in pixels
        var coordinatesWidth = (canvas.width - endEmpty) / lengthOfScale; //pixel to AA
        var skip = getSkipSize(lengthOfScale, coordinatesWidth);
    
        //clear canvas from before
        context.clearRect(0, 0, canvasWidth, canvasHeight);
    
        //gridlines
        this.drawProteinGridLines(context, coordinatesWidth, startHeight, lengthOfScale * coordinatesWidth, skip,endEmpty);
    
        //line graphics
        createBaseLine(context, 0, startHeight, lengthOfScale * coordinatesWidth, lineThickness);
    }

    /** 
 * this is for the transcript and protein scales. add gridline after constant skip
 * distance calculated and the position.
 */
drawProteinGridLines(context, coordinatesWidth, startHeight, canvasWidth, skip, endEmpty) {
    var gridLength = 30;
    var lineheight = startHeight - (gridLength - 8) / 2;
    var noNumberZone=-50;//in px (in the end)
    for (var i = skip - (this.zoomInStart/3 % skip);
        (i * coordinatesWidth +noNumberZone) < canvasWidth-endEmpty; i = i + skip) {
        context.fillRect(i * coordinatesWidth, lineheight, 1, gridLength);

    }
    
    //draw number
    context.font = "20px Calibri";
    context.fillText("Nucleotide", 10, 30);
    context.fillText("Amino acid", 10, 125);

    //i is in nuclotides
    for (var i = skip - (this.zoomInStart/3 % skip);
        (i * coordinatesWidth ) < canvasWidth-endEmpty; i = i + skip) {
        
        //nucloteide number
        context.save();
        context.translate(coordinatesWidth * i + 3, lineheight - 3);
        context.rotate(-Math.PI / 8);
        context.fillStyle = "black"
        context.font = "15px Calibri";
        context.textAlign = "left";
        context.fillText(numberToTextWithCommas(i * 3+this.zoomInStart), 0, 0);
        context.restore();
        
        //amino acid number
        context.save();
        context.translate(coordinatesWidth * i, lineheight + 40);
        context.rotate(Math.PI / 8);
        context.fillStyle = "black"
        context.font = "15px Calibri";
        context.textAlign = "left";
        context.fillText(numberToTextWithCommas(Math.round(i+this.zoomInStart/3)), 0, 0);
        context.restore();
    }
}

    

}