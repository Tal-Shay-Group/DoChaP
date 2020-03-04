/*
    this file focuses on actual graphics. drawing the shapes in proportions, sizes and length.
    each view is coded differently and we hope to write code that can be easily handled and managed.
*/

/**
 * builds gridlines after constant skip. for genomic view only
 * @param {*} contextT context of the canvas wanted
 * @param {*} beginningEmpty pixels empty in start
 * @param {*} coordinatesWidth needed for pixal to nuc conversion 
 * @param {*} canvasHeight 
 * @param {*} canvasWidth 
 * @param {*} lengthOfGene in nuc units
 * @param {*} startCoordinate 
 * @param {boolean} isinMiddle  gridline from middle or from bottom mostly
 * @param {*} startHeight length from top
 */

// function createGridLines(contextT, beginningEmpty, coordinatesWidth, canvasHeight, canvasWidth, lengthOfGene, startCoordinate, isinMiddle, startHeight) {
//     var gridLength = 10;
//     var startHeight = startHeight - gridLength;
//     contextT.fillStyle = "#bfbfbf";
//     if (!isinMiddle) {
//         gridLength = 5;
//         startHeight = canvasHeight - gridLength;
//         contextT.fillStyle = "black";
//     }

//     var skip = getSkipSize(lengthOfGene, coordinatesWidth);
//     // contextT.fillRect(beginningEmpty, startHeight, 1,gridLength);
//     var secondCoordinate = skip - (startCoordinate % skip); //the length till the next rounded after start
//     for (var i = secondCoordinate;
//         (i * coordinatesWidth + 2) < canvasWidth; i = i + skip) {
//         contextT.fillRect((i * coordinatesWidth) + beginningEmpty, startHeight, 1, gridLength);
//     }

// }

function gridCoordinates(start,skip, coordinatesWidth, canvasWidth, beginningEmpty, endEmpty, strand ,cutOffStart, cutOffLength, spaceAfterCut) {
    var Xcoordinates = [];
    var geneCoordinate = start - (start % skip) + skip;
    var secondCoordinate = skip - (start % skip); //the length till the next rounded after start
    var needCut= (cutOffStart!=-1 && cutOffLength!=-1) ; // checks if we need cut
    
    for (var i = secondCoordinate;
        (i * coordinatesWidth) + 2 < canvasWidth; i = i + skip) {
            
            if(needCut && geneCoordinate>cutOffStart){
                //doing cut
                needCut=false;
                var afterCut=cutOffStart+cutOffLength;
                geneCoordinate= afterCut- (afterCut % skip) + skip
                i=i+50+skip - (afterCut % skip); //so the line is where the after *skip* is also applied and *cut* is applied
            }
            var grid=new Object();
            grid.text=numberToTextWithCommas(geneCoordinate);
            if(strand=='+'){
                grid.x=(i * coordinatesWidth) + beginningEmpty;
            }
            else if (strand=='-'){
                grid.x=canvasWidth -endEmpty -(i * coordinatesWidth)
            }
        Xcoordinates.push(grid);
        geneCoordinate = geneCoordinate + skip;
    }
    return Xcoordinates
}


/** 
 * selecting how musch is for skip. depends on proportions between the canvas size and protein size
 */
function getSkipSize(lengthOfScale, coordinatesWidth) { ///length in base units, cw is the convertor
    var skip = 1000; //skip is in genomic units
    if (skip * coordinatesWidth < 0.005) {
        skip = 50000000; //fifty million
    } else if (skip * coordinatesWidth < 0.01) {
        skip = 10000000; //ten million
    } else if (skip * coordinatesWidth < 0.05) {
        skip = 5000000; //5 million
    } else if (skip * coordinatesWidth < 0.5) {
        skip = 1000000;
    } else if (skip * coordinatesWidth < 1) {
        skip = 500000;
    } else if (skip * coordinatesWidth < 1.3) {
        skip = 100000;
    } else if (skip * coordinatesWidth < 3.5) {
        skip = 50000;
    } else if (skip * coordinatesWidth < 20) {
        skip = 10000;
    } else if (skip * coordinatesWidth < 40) {
        skip = 5000;
    } else if (skip * coordinatesWidth > 800) {
        skip = 50;
    } else if (skip * coordinatesWidth > 280) {
        skip = 100;
    } else if (skip * coordinatesWidth > 140) {
        skip = 300;
    } else if (skip * coordinatesWidth > 120) {
        skip = 500;
    }
    return skip;
    /*info on long genes:

        select *
        from (select gene_id, max(tx_end)-min(tx_start) as length from transcripts group by gene_id)
        order by length desc

    */
}

/**
 * change int to string with comma for thaousands
 * @param {int} number 
 */
function numberToTextWithCommas(number) {
    //from stackOverFlow
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

//build an horizontal line 
function createBaseLine(context, startX, startY, width, lineThickness) {
    context.beginPath();
    context.fillStyle = "black";
    context.rect(startX, startY, width, lineThickness);
    context.fill();
    context.closePath();
}