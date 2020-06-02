class ProteinGraphicLayout {
    /**
     * 
     * @param {String} canvasID canvas id in html
     * @param {ProteinScale} proteinScale the current protein scale
     */
    constructor(canvasID,proteinScale) {
        this.canvas = document.getElementById(canvasID);
        this.context =  this.canvas.getContext("2d");
        this.canvasHeight =  this.canvas.height;
        this.canvasWidth =  this.canvas.width;
        this.lineThickness = 8;
        this.startHeight = 70; //space from top
        this.lengthOfScale = (proteinScale.zoomInEnd - proteinScale.zoomInStart) / 3; //both in necluotides
        this.endEmpty = 50; //in pixels
        this.coordinatesWidth = ( this.canvas.width -  this.endEmpty) /  this.lengthOfScale; //pixel to AA
        this.skip = getSkipSize( this.coordinatesWidth);

   
    }
}