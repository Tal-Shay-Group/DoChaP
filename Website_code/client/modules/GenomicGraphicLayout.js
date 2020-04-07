class GenomicGraphicLayout {
    constructor(canvasID,gene) {
        this.canvas = document.getElementById(canvasID);
        this.context = this.canvas.getContext("2d");
        this.canvasHeight = this.canvas.height;
        this.canvasWidth = this.canvas.width;
        
        //default parameters for graphic layout
        this.lineThickness = 4;
        this.startHeight = 50;
        this.beginningEmpty = 10; //in pixels
        this.endEmpty = 5; //in pixels
        this.spaceAfterCut = 50;
        var length= gene.end - gene.start;

        //compution attributes
        this.coordinatesWidth = (this.canvasWidth - this.beginningEmpty -  this.endEmpty) /length;
        this.skip = getSkipSize(this.coordinatesWidth);
        
        //cut-off if needed
        if(gene.cutOffStart != -1 && gene.cutOffLength!=-1){
            this.coordinatesWidth = (this.canvasWidth - this.beginningEmpty -  this.endEmpty) /(length-gene.cutOffLength);
            this.skip = getSkipSize(this.coordinatesWidth);
            this.coordinatesWidth = (this.canvasWidth - this.beginningEmpty - this.endEmpty - this.spaceAfterCut) / (length-gene.cutOffLength);
            this.cutX=(gene.cutOffStart-gene.start)*this.coordinatesWidth+ this.beginningEmpty;
            if(gene.strand=='-'){
                this.cutX=this.canvasWidth- (gene.cutOffStart-gene.start)*this.coordinatesWidth-this.endEmpty-this.spaceAfterCut;
            }
        }
   
    }
}