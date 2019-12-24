/*
    this file focuses on actual graphics. drawing the shapes in proportions, sizes and length.
    each view is coded differently and we hope to write code that can be easily handled and managed.
*/
// transcript view consists of line and rectangles with exon order names
function buildGenomicView(canvasID, transcript) {
    var exons = transcript.exons;
    if (exons == undefined) {
        throw "wrong format for geneCanvasGraphics";
    }

    //calculations
    //var colorDict = transcript.colorDict;
    var canvasT = document.getElementById(canvasID); //$('#' + canvasID); 
    var contextT = canvasT.getContext("2d");
    var canvasHeight = canvasT.height;
    var canvasWidth = canvasT.width;
    var lineThickness = 2;
   // var spacing = (canvasHeight - lineThickness) / 2; //devide by 2 so its the middle
    var spacing = 50;
    var lengthOfGene = transcript.length;
    var beginningEmpty=10; //in pixels
    var endEmpty=5; //in pixels
    var coordinatesWidth = (canvasT.width-beginningEmpty-endEmpty) / lengthOfGene;
    var startCoordinate=transcript.startCoordinate;
    
    contextT.fillStyle = "white";
    contextT.fillRect(0, 0, canvasWidth, canvasHeight);
    //contextT.fill();

    //gridlines
    createGridLines(contextT,beginningEmpty,coordinatesWidth,canvasHeight,canvasWidth,lengthOfGene,startCoordinate,true,spacing);

    //line graphics
    createBaseLine(contextT, 0, spacing, canvasWidth, lineThickness);

    //exon graphics
    for (var i = 0; i < exons.length; i++) {
        //calculate
        var exonWidth = Math.max(3, (exons[i].transcriptViewEnd - exons[i].transcriptViewStart + 1) * coordinatesWidth);
        const exonHeight = 70;
        const exonX = exons[i].transcriptViewStart * coordinatesWidth+beginningEmpty;
        const exonY = spacing - exonHeight / 2;
        //draw
        drawExonInGenomicView(contextT, i, exonX, exonY, exonWidth, exonHeight, exons[i].color,false,exons[i].isUTRStart,exons[i].isUTREnd,exons[i].isUTRAll,coordinatesWidth);
    }

}
// exon view consists  exon rectangles filling the canvas in order and proportions
function buildTranscriptView(canvasID, transcript) {
    //calculations
    var exons = transcript.exons;
    var colorDict = transcript.colorDict;
    var canvasE = document.getElementById(canvasID);
    var contextE = canvasE.getContext("2d");
    var canvasHeight = canvasE.height;
    var canvasWidth = canvasE.width;
    var lineThickness = 4;
    var spacing = (canvasHeight - lineThickness) / 2; //devide by 2 so its the middle
    var coordinatesWidth = ((canvasWidth)/transcript.maxProteinLength) ;
    contextE.clearRect(0, 0, canvasWidth, canvasHeight);
    //var currX = 0; //used if the area is calculated with genomePositions

    //line graphics
    //createBaseLine(contextE, 0, spacing, canvasWidth, lineThickness);

    //exon graphics
    for (var i = 0; i < exons.length; i++) {
        if(exons[i].exonViewStart==0){
            continue;
        }
        exonWidth = (exons[i].exonViewEnd - exons[i].exonViewStart + 1) * coordinatesWidth;
        exonHeight = 25;
        exonX = exons[i].exonViewStart * coordinatesWidth; //currX;
        exonY = spacing - exonHeight / 2;
        if( exonX+exonWidth>=canvasWidth){
            exonWidth=Math.max(1,canvasWidth-exonX-2);
        }
        //for now its the same exon drawer
        drawExonInTranscriptView(contextE, i, exonX, exonY, exonWidth, exonHeight, exons[i].color,false);

        //for now its the same exon drawer
        /*contextE.fillStyle = colorDict[i];
        contextE.fillRect(exonX, exonY, exonWidth, exonHeight);

        contextE.fillStyle = "white";
        contextE.fillText("" + (i + 1), exonX + 8, exonY + 8);

        contextE.strokeStyle = "black";
        contextE.strokeRect(exonX, exonY, exonWidth, exonHeight);
        */
        //currX = exonX + exonWidth;
    }
}
//protein view consists of a line and currently circles in color of exons they are made of in gradient manner
function buildProteinView(canvasID, transcript) {
    var exons = transcript.exons;
    var colorDict = transcript.colorDict;
    var canvasP = document.getElementById(canvasID);
    var contextP = canvasP.getContext("2d");
    var canvasHeight = canvasP.height;
    var canvasWidth = canvasP.width;
    var proteinLength= transcript.proteinLength;
    var lineThickness = 4;
    // var spacing = (canvasHeight - lineThickness) / 2; //devide by 2 so its the middle
    var spacing=25;
    //domains
    //calculate places with no non-coding areas
    var domainsInProtein = transcript.domains; //[]
    var coordinatesWidth =((canvasWidth)/transcript.maxProteinLength) ;

    contextP.clearRect(0, 0, canvasWidth, canvasHeight);

    //line. 
    var proteinEndInView=proteinLength*coordinatesWidth;
    createBaseLine(contextP, 0, spacing, proteinEndInView, lineThickness);

    for (var i = 0; i < domainsInProtein.length; i++) {
        //calculations
        domainWidth = (domainsInProtein[i].end - domainsInProtein[i].start) * coordinatesWidth;
        domainHeight = 45;
        domainX = domainsInProtein[i].start * coordinatesWidth;
        domainY = spacing - domainHeight / 2;
        overlap = false;//domainsInProtein[i].overlap;
        shapeID=0; //currently its random
        domainText=domainsInProtein[i].showText;
        if( domainX+domainWidth>=canvasWidth){
            domainWidth=Math.max(1,canvasWidth-domainX-2);
        }
        //calculate domain colors and gradient
        gradient = getGradientForDomain(domainX, domainX + domainWidth, domainsInProtein[i], spacing, exons, contextP);
        
        //domain draw
        drawDomainInProteinView(contextP, domainX, domainY, domainHeight, domainWidth, gradient, domainsInProtein[i].name,overlap,shapeID,domainText);
    }
 
}
function buildScaleView(canvasID, scale) {

    //calculations
    var canvasS = document.getElementById(canvasID);
    var contextS = canvasS.getContext("2d");
    var canvasHeight = canvasS.height;
    var canvasWidth = canvasS.width;
    var lineThickness = 8;
    var spacing = 70; //space from top
    var lengthOfScale = scale.end-scale.start; //both in necluotides
    var beginningEmpty=10; //in pixels
    var endEmpty=5; //in pixels
    var coordinatesWidth = (canvasS.width-beginningEmpty-endEmpty) / lengthOfScale;
    var skip=getSkipSize(lengthOfScale,coordinatesWidth);
    var strand=scale.strand;
    var chromosomeName=scale.chromosomeName;
    contextS.clearRect(0, 0, canvasWidth, canvasHeight);
    //gridlines
    createGridLines(contextS,beginningEmpty,coordinatesWidth,spacing,canvasWidth,lengthOfScale,scale.start,false,canvasHeight);

    //line graphics
    createBaseLine(contextS, 0, spacing, canvasWidth, lineThickness);
    
    //scope text
    //contextS.font = "15px Ariel bold";
    //contextS.textAlign = "left";
    //contextS.fillText(chromosomeName+":"+numberToTextWithCommas(scale.start)+"-"+numberToTextWithCommas(scale.end), 1, 14);
    
    //labels for counting
    createNumberLabelsForScale(contextS,lengthOfScale,skip,coordinatesWidth,beginningEmpty,spacing,scale.start);
    
    
    //draw arrow 
    drawArrow(contextS,strand,200,(canvasWidth-200)/2,110);


}

function buildScaleViewForProtein(canvasID, proteinScale) {

    //calculations
    var canvasS = document.getElementById(canvasID);
    var contextS = canvasS.getContext("2d");
    var canvasHeight = canvasS.height;
    var canvasWidth = canvasS.width;
    var lineThickness = 8;
    var spacing = 70; //space from top
    var lengthOfScale = proteinScale.length/3; //both in necluotides
    var coordinatesWidth = (canvasS.width) / lengthOfScale;
    //var skip=100;
    var skip=getSkipSize(lengthOfScale,coordinatesWidth);
    contextS.clearRect(0, 0, canvasWidth, canvasHeight);

    //gridlines
    createProteinGridLines(contextS,coordinatesWidth,spacing,canvasWidth,skip);

    //line graphics
    createBaseLine(contextS, 0, spacing, canvasWidth, lineThickness);
     
    

}


function createGridLines(contextT,beginningEmpty,coordinatesWidth,canvasHeight,canvasWidth,lengthOfGene,startCoordinate,isinMiddle,spacing){
    var gridLength=10;
    var startHeight=spacing-gridLength;
    contextT.fillStyle ="#bfbfbf";
    if(!isinMiddle){
        gridLength=5;
        startHeight=canvasHeight-gridLength;
        contextT.fillStyle ="black";
    }
    
    
    var skip=getSkipSize(lengthOfGene,coordinatesWidth);    
   // contextT.fillRect(beginningEmpty, startHeight, 1,gridLength);
    var secondCoordinate=skip-(startCoordinate%skip); //the length till the next rounded after start
    for(var i=secondCoordinate; (i*coordinatesWidth+2)<canvasWidth; i=i+skip){
        contextT.fillRect((i*coordinatesWidth)+beginningEmpty, startHeight, 1,gridLength);
    }
    
}
function createProteinGridLines(context,coordinatesWidth,startHeight,canvasWidth,skip){
    var gridLength=30;
    var lineheight= startHeight-(gridLength-8)/2;
    for(var i=0; (i*coordinatesWidth+2)<canvasWidth; i=i+skip){
        context.fillRect(i*coordinatesWidth, lineheight, 1,gridLength);
        
    }
 
    //draw number
    context.font = "15px Calibri";
    context.fillText("nucleotide",10,30);
    context.fillText("amino acid",10,125);
     for(var i=0; (i*coordinatesWidth+50)<canvasWidth;i=i+skip){
       context.save();
        context.translate(coordinatesWidth*i+3,lineheight-3);
        context.rotate(-Math.PI/8);
        context.fillStyle = "black" 
        context.font = "15px Calibri";
        context.textAlign = "left";
        context.fillText(numberToTextWithCommas(i*3), 0, 0);
        context.restore();  
        //nucleotide number
        context.save();
        context.translate(coordinatesWidth*i,lineheight+40);
        context.rotate(Math.PI/8);
        context.fillStyle = "black" 
        context.font = "15px Calibri";
        context.textAlign = "left";
        context.fillText(numberToTextWithCommas(i), 0, 0);
        context.restore();
     }
        

}


function createNumberLabelsForScale(context,lengthOfScale,skip,coordinatesWidth,beginningEmpty,spacing,scaleStart){
    //first coordinate
      /*  context.save();
        context.translate(beginningEmpty,spacing-8);
        context.rotate(-Math.PI/8);
        context.fillStyle = "black" 
        context.font = "15px Calibri";
        context.textAlign = "left";
        context.fillText(numberToTextWithCommas(scaleStart), 0,  0);
        context.restore();*/
    var currLabel=scaleStart-(scaleStart%skip)+skip;// space in the beginning
    var endEmpty=50/coordinatesWidth;//its 30 pixels in genome units
    for( var i=(skip-(scaleStart%skip)); i<lengthOfScale-endEmpty ; i=i+skip){
        context.save();
        context.translate(coordinatesWidth*i+beginningEmpty,spacing-8);
        context.rotate(-Math.PI/8);
        context.fillStyle = "black" 
        context.font = "15px Calibri";
        context.textAlign = "left";
        context.fillText(numberToTextWithCommas(currLabel), /*coordinatesWidth*i+beginningEmpty*/0,  /*spacing-8*/0);
        context.restore();
        currLabel=currLabel+skip
    }
}

function getSkipSize(lengthOfScale,coordinatesWidth){ ///length in base units, cw is the convertor
    var skip=1000; //skip is in genomic units
    if (skip*coordinatesWidth<3 ){
        skip=100000;
    }else if (skip*coordinatesWidth<30 ){
        skip=10000;
    }else if (skip*coordinatesWidth<40 ){
        skip=5000;
    }
    else if(skip*coordinatesWidth>280){
        skip=100;
    } 
     else if(skip*coordinatesWidth>140){
        skip=300;
    }
     else if (skip*coordinatesWidth>120){
        skip=500;
    }
        return skip;
    
}

function drawArrow(context,strand,arrowLength,width,height){ //width and height in which the arrow starts
    var arrowWidthLine=8;
    //baseline
    context.beginPath();
    context.moveTo(width, height);
    context.lineTo(width+arrowLength, height);
    context.closePath();
    context.stroke();
    //arrow
    if(strand=='+'){
        context.beginPath();
        context.moveTo(width+arrowLength-arrowWidthLine, height-arrowWidthLine);
        context.lineTo(width+arrowLength, height);
        context.lineTo(width+arrowLength-arrowWidthLine, height+arrowWidthLine);
        context.closePath();
        context.fill();
    }else if(strand=='-'){
        context.beginPath();
        context.moveTo(width+arrowWidthLine, height-arrowWidthLine);
        context.lineTo(width,height);
        context.lineTo(width+arrowWidthLine, height+arrowWidthLine);
        context.closePath();
        context.fill();
    }
    context.font = "20px Calibri";
    context.textAlign="center";
    context.fillText("strand "+ strand, width+(arrowLength/2),height-5);
}

//select a totally random color 
function getRandomColor() {
    var letters = '0123456789ABCDEF';
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

function getcolorFromList(colorArr) {
    i=colorArr.length%3;
    if(i==0){
        i=0;
    } else if (i==1){
        i=colorArr.length-1;
    } else if (i==2){
        i=(colorArr.length+1)/2;
    }
    return  colorArr.splice(i, 1);
    //return  colorArr.splice(0, 1);
}


function placeRedColor(number) {
    var letters = '0123456789ABCDEF';
    var color = '#FF';
    var placePicked=number % (16^4);
    for (var i = 0; i < 4; i++) {
        color += letters[placePicked-Math.floor(placePicked/16)];
    }
    return color;
}

function numberToTextWithCommas(number){
    //from internet! what to do with that
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
function placeCorrolationColor(number) {
    var letters = '0123456789ABCDEF';
    var color = '#';//+letters[rand1]+letters[rand1];
    var placePicked=number % Math.pow(16,6);
    for (var i = 0; i < 6; i++) {
        color += letters[placePicked-Math.floor(placePicked/16)*16];
        placePicked=Math.floor(placePicked/16);
    }
    return color;
}


/*calculate domain positions if given in genome postions (absoulute but includes introns).
not needed anymore but may be handy in the future*/
function domainPositionsGivenGenomePositions(domains) {
    var domainNoIntronsCoordinates = [];
    for (var i = 0; i < domains.length; i++) { //assumption both exons+domains not overlapping with themselves and in order
        domainNoIntronsCoordinates[i] = [0, 0];
        for (var j = 0; j < exons.length; j++) {
            var exonSize = exons[j][1] - exons[j][0];
            var domainSize = domains[i][1] - domains[i][0]; //may include intron length
            if (domains[i][0] > exons[j][1]) { 
                //exon before domain
                domainNoIntronsCoordinates[i][0] = domainNoIntronsCoordinates[i][0] + exonSize;
                domainNoIntronsCoordinates[i][1] = domainNoIntronsCoordinates[i][1] + exonSize;
            } else if (exons[j][0] <= domains[i][0] && domains[i][0] <= exons[j][1] && domains[i][1] <= exons[j][1]) { 
                // all in
                domainNoIntronsCoordinates[i][0] = domainNoIntronsCoordinates[i][0] + domains[i][0] - exons[j][0];
                domainNoIntronsCoordinates[i][1] = domainNoIntronsCoordinates[i][1] + domains[i][0] - exons[j][0] + domainSize;
            } else if (exons[j][0] <= domains[i][0] && domains[i][0] <= exons[j][1]) { 
                //starting in this exons but not finishing
                domainNoIntronsCoordinates[i][0] = domainNoIntronsCoordinates[i][0] + domains[i][0] - exons[j][0];
                domainNoIntronsCoordinates[i][1] = domainNoIntronsCoordinates[i][1] + exonSize; 
            } else if (domains[i][0] < exons[j][0] && domains[i][0] <= exons[j][1] && exons[j][0] <= domains[i][1]) {
                 // the end is in other exon
                domainNoIntronsCoordinates[i][1] = domainNoIntronsCoordinates[i][1] + domains[i][1] - exons[j][0];
            } else {
                break;
            }
        }
    }
    return domainNoIntronsCoordinates;
}

//calculations of gradient color
function getGradientForDomain(start, end, domainCoordinates, spacing, exons, context) { //exons are absolute position for this to work
    var gradient = context.createLinearGradient(start, spacing, end, spacing); //contextP only for domains now
    var whiteLineRadius = 8;

    for (var i = 0; i < exons.length; i++) {
        if (exons[i].exonViewStart <= domainCoordinates.start && domainCoordinates.start <= exons[i].exonViewEnd && exons[i].exonViewStart <= domainCoordinates.end && domainCoordinates.end <= exons[i].exonViewEnd) {
            //no junctions so only one color
            return exons[i].color;
        }
        if (exons[i].exonViewStart <= domainCoordinates.start && domainCoordinates.start <= exons[i].exonViewEnd) {
            //the starting color for the domain
            gradient.addColorStop(0, exons[i].color);
            var position = Math.max(0, (exons[i].exonViewEnd - domainCoordinates.start - whiteLineRadius) / (domainCoordinates.end - domainCoordinates.start));
            gradient.addColorStop(position, exons[i].color);
            //white line (if wanted)
            gradient.addColorStop((exons[i].exonViewEnd - domainCoordinates.start) / (domainCoordinates.end - domainCoordinates.start), "white");
        }
        if (exons[i].exonViewStart <= domainCoordinates.end && domainCoordinates.end <= exons[i].exonViewEnd) {
            //ending color for domain
            var position = Math.min(1, (exons[i].exonViewStart - domainCoordinates.start + whiteLineRadius) / (domainCoordinates.end - domainCoordinates.start));
            gradient.addColorStop(position, exons[i].color);
            gradient.addColorStop(1, exons[i].color);
        }
        if (domainCoordinates.start <= exons[i].exonViewStart && exons[i].exonViewEnd <= domainCoordinates.end) {
            //color for exon in the middle (not starting or finishing)
            
            //white lines (if wanted)
            gradient.addColorStop((exons[i].exonViewStart - domainCoordinates.start) / (domainCoordinates.end - domainCoordinates.start), "white");
            gradient.addColorStop((exons[i].exonViewEnd - domainCoordinates.start) / (domainCoordinates.end - domainCoordinates.start), "white");

            //main coloring
            var position1 = Math.min(1, (exons[i].exonViewStart - domainCoordinates.start + whiteLineRadius) / (domainCoordinates.end - domainCoordinates.start));
            var position2 = Math.max(0, (exons[i].exonViewEnd - domainCoordinates.start - whiteLineRadius) / (domainCoordinates.end - domainCoordinates.start));
            gradient.addColorStop(position1, exons[i].color);
            gradient.addColorStop(position2, exons[i].color);
        }
    }

    return gradient;
}

//build an horizontal line 
function createBaseLine(context, startX, startY, width, lineThickness) {
    context.beginPath();
    context.fillStyle = "black";
    context.rect(startX, startY, width, lineThickness);
    context.fill();
    context.closePath();
}

//draw rectangle, border and text or polygon if not all exon is in cds. note that utrStart and utrEnd are bases in the beginning or end that are out of the cds. if all is out utrAll is true
function drawExonInGenomicView(context, index, exonX, exonY, exonWidth, exonHeight, color,showText,utrStart,utrEnd,utrAll,coordinatesWidth) {
   if(utrStart==undefined && utrEnd==undefined && (!utrAll)){
       //background color
    context.fillStyle = color;
    context.fillRect(exonX, exonY, exonWidth, exonHeight);
    //border
    context.strokeStyle = "black";
    context.strokeRect(exonX, exonY, exonWidth, exonHeight);
   }else if(utrAll){
    //background color
   context.fillStyle = color;
   context.fillRect(exonX, exonY+(exonHeight/4), exonWidth, exonHeight/2);
   //border
   context.strokeStyle = "black";
   context.strokeRect(exonX, exonY+(exonHeight/4), exonWidth, exonHeight/2);
   } else if(utrStart!=undefined && utrEnd==undefined){
    context.beginPath();
    context.moveTo(exonX, exonY+(exonHeight/4));
    context.lineTo(exonX, exonY+(3*exonHeight/4));
    context.lineTo(exonX+utrStart*coordinatesWidth,  exonY+(3*exonHeight/4));
    context.lineTo(exonX+utrStart*coordinatesWidth,exonY+exonHeight);
    context.lineTo(exonX+exonWidth,exonY+exonHeight);
    context.lineTo(exonX+exonWidth,exonY);
    context.lineTo(exonX+utrStart*coordinatesWidth,exonY);
    context.lineTo(exonX+utrStart*coordinatesWidth, exonY+(exonHeight/4));
    context.closePath();
    context.fillStyle = color;
    context.fill();
    context.strokeStyle = "black";
    context.stroke();
   } else if(utrStart==undefined && utrEnd!=undefined){
    context.beginPath();
    context.moveTo(exonX, exonY);
    context.lineTo(exonX, exonY+exonHeight);
    context.lineTo(exonX+utrEnd*coordinatesWidth,exonY+exonHeight );
    context.lineTo(exonX+utrEnd*coordinatesWidth, exonY+(3*exonHeight/4));
    context.lineTo(exonX+exonWidth,exonY+(3*exonHeight/4));
    context.lineTo(exonX+exonWidth,exonY+(exonHeight/4));
    context.lineTo(exonX+utrEnd*coordinatesWidth,exonY+(exonHeight/4));
    context.lineTo(exonX+utrEnd*coordinatesWidth, exonY);
    context.closePath();
    context.fillStyle = color;
    context.fill();
    context.strokeStyle = "black";
    context.stroke();
   } 
   else if(utrStart!=undefined && utrEnd!=undefined){
    context.beginPath();
    context.moveTo(exonX, exonY+(exonHeight/4));
    context.lineTo(exonX, exonY+(3*exonHeight/4));
    context.lineTo(exonX+utrStart*coordinatesWidth,  exonY+(3*exonHeight/4));
    context.lineTo(exonX+utrStart*coordinatesWidth,exonY+exonHeight);
    context.lineTo(exonX+utrEnd*coordinatesWidth,exonY+exonHeight );
    context.lineTo(exonX+utrEnd*coordinatesWidth, exonY+(3*exonHeight/4));
    context.lineTo(exonX+exonWidth,exonY+(3*exonHeight/4));
    context.lineTo(exonX+exonWidth,exonY+(exonHeight/4));
    context.lineTo(exonX+utrEnd*coordinatesWidth,exonY+(exonHeight/4));
    context.lineTo(exonX+utrEnd*coordinatesWidth, exonY);
    context.lineTo(exonX+utrStart*coordinatesWidth,exonY);
    context.lineTo(exonX+utrStart*coordinatesWidth, exonY+(exonHeight/4));
    context.closePath();
    context.fillStyle = color;
    context.fill();
    context.strokeStyle = "black";
    context.stroke();
   }
    
    //text
    if(showText){
        context.fillStyle = "black" //"white"; //for text
    context.font = "20px Calibri";
    context.fillText("" + (index + 1), exonX + exonWidth / 2, exonY + (exonHeight / 2) - 8);
    }
    
}

//draw rectangle, border and text
function drawExonInTranscriptView(context, index, exonX, exonY, exonWidth, exonHeight, color,showText) {
    //background color
    context.fillStyle = color;
    context.fillRect(exonX, exonY, exonWidth, exonHeight);

    //border
    context.strokeStyle = "black";
    context.strokeRect(exonX, exonY, exonWidth, exonHeight);

    //text
    if(showText){
        context.fillStyle = "black" //"white"; //for text
    context.font = "20px Calibri";
    context.fillText("" + (index + 1), exonX + exonWidth / 2, exonY + (exonHeight / 2) - 8);
    }
}

//finds the area needed for all exons and calculates the length of each coordinate so it will perfectly fit the canvas bar
function getCoordinatesWidth(exons, canvasWidth) { //exons is an array of [startCoordinate,endCoordinate] 
    let coordinatesWidth = 0;
    for (var i = 0; i < exons.length; i++) {
        coordinatesWidth = coordinatesWidth + exons[i].exonViewEnd - exons[i].exonViewStart + 1; //only coding areas stay (good for genome or abs positions)
    }
    return canvasWidth / coordinatesWidth; //divides so we know how wide is each coordinate
}


function drawDomainInProteinView(context, domainX, domainY, domainHeight, domainWidth, gradient, name,overlap,shapeID,domainText) {   
    //background color
    context.beginPath();
    context.fillStyle = gradient;
    if(shapeID==0){
        context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, domainWidth / 2, domainHeight / 2, 0, 0, 2 * Math.PI);
    } else if(shapeID==1){
        context.beginPath();
        context.moveTo(domainX, domainY);
        context.lineTo(domainX+ domainWidth/2,domainY+ domainHeight);
        context.lineTo(domainX+ domainWidth,domainY);
        context.closePath();
    }
    
    if(overlap){
        context.globalAlpha=0.7;  
        context.fill();
        context.globalAlpha=1;
    }else{ 
        context.fill();
    }
    
    //border
    context.beginPath();
    context.strokeStyle = "black";
    if(shapeID==0){
        context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, domainWidth / 2, domainHeight / 2, 0, 0, 2 * Math.PI);
    }else if(shapeID==1){
        context.beginPath();
        context.moveTo(domainX, domainY);
        context.lineTo(domainX+ domainWidth/2,domainY+ domainHeight);
        context.lineTo(domainX+ domainWidth,domainY);
        context.closePath();
    }
    context.stroke();

    //text
    /*context.fillStyle = "black"; //for text
    context.font = "bold 14px Calibri";
    context.shadowColor = "black";
    context.textBaseline = 'middle';
    context.textAlign = "center";
    context.fillText(name, domainX + domainWidth / 2, domainY + domainHeight+8);
    */

    if(domainText){
        context.save();
    context.translate(domainX+ domainWidth/2,domainY + domainHeight+8);
    context.rotate(Math.PI/16);
    context.fillStyle = "black"; //for text
    context.font = "bold 13px Calibri";
    context.shadowColor = "black";
    context.textAlign = "left";
    context.fillText(name,0,0);
    context.restore();
    }
    

}       
    