/*
this file was created to suit our needs for gene graphics. since the db only serves us with raw data.
this file calculates and decides what to forward to the website and the graphic works. this can be thought
as an controller or as an adapter. only 'runGenesCreation' function will be used but it will call the
other functions as needed.

*/
function runGenesCreation(result, ignorePredictions, preferences) {
    geneList = [];
    colorByLength = undefined;
    start = undefined;
    end = undefined;
    proteinStart =undefined;
    proteinEnd=undefined;

    if (preferences != undefined ) {
        colorByLength = preferences.colorByLength ? getColorForLength(result, ignorePredictions) : undefined;
        start = preferences.start;
        end = preferences.end;
        proteinStart = preferences.proteinStart;
        proteinEnd = preferences.proteinEnd;
    }


    for (var i = 0; i < result.genes.length; i++) {
        geneList.push(new Gene(result.genes[i], ignorePredictions,colorByLength,start,end,proteinStart,proteinEnd));
    }

    return geneList;
}

/** 
 * selecting how musch is for skip. depends on proportions between the canvas size and protein size
 */
function getSkipSize(coordinatesWidth) { ///length in base units, cw is the convertor
    var skip = 1000; //skip is in genomic units
    if (skip * coordinatesWidth < 0.005) {
        skip = 50000000; //fifty million
    } else if (skip * coordinatesWidth < 0.01) {
        skip = 10000000; //ten million
    } else if (skip * coordinatesWidth < 0.05) {
        skip = 5000000; //5 million
    } else if (skip * coordinatesWidth < 0.1) {
        skip = 1000000;
    } else if (skip * coordinatesWidth < 0.35) {
        skip = 500000;
    } else if (skip * coordinatesWidth < 1.3) {
        skip = 100000;
    } else if (skip * coordinatesWidth < 3) {
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


//select a totally random color 
function getRandomColor() {
    var letters = '0123456789ABCDEF';
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

//selecting color from list (deterministic yet not in order)
function getcolorFromList(colorArr) {
    if (colorArr.length <= 1) {
        colorArr.push.apply(colorArr,  ["#DACCFF", "#9B72FF","#B627FC",  "#DE3D3D", "#FF6262", "#f5b0cb", "#ffccd8",                
        "#CD923C", "#FFBB8F","#FD9900", "#ffb90f", "#ffd700", "#FFFC3B", "#FFF599", "#FFFED3", "#ccff00", "#20F876", "#63C37F","#5BAF2F",
          "#2D79FF", "#00ccff", "#7BEAD2","#beebe9"
    ]);
    }
        i = colorArr.length % 4;
        if (i == 0) {
            i = 0;
        } else if (i == 1) {
            i = colorArr.length - 1;
        } else if (i == 2) {
            i = colorArr.length / 3;
        } else if (i == 3) {
            i = colorArr.length * 2 / 3;
        }
    return colorArr.splice(i, 1)[0];
}

/**
 * using a number to select color (same exons receive same colors)
 * @param {number that somehow represent exon} number e.g. start coordinate
 */
function placeRedColor(number) {
    var letters = '0123456789ABCDEF';
    var color = '#FF';
    var placePicked = number % (16 ^ 4);
    for (var i = 0; i < 4; i++) {
        color += letters[placePicked - Math.floor(placePicked / 16)];
    }
    return color;
}



/**|
 * color by place so the color changes as the position changes
 */
function placeCorrolationColor(number) {
    var letters = '0123456789ABCDEF';
    var color = '#';
    var placePicked = number % Math.pow(16, 6);
    for (var i = 0; i < 6; i++) {
        color += letters[placePicked - Math.floor(placePicked / 16) * 16];
        placePicked = Math.floor(placePicked / 16);
    }
    return color;
}

/**
 * getting all length available and choosing unique colors
 * @param {server result} result what the db sends
 */
function getColorForLength(result) {
    //comapre function 
    function compare(a, b) {
        aLength = a.genomic_end_tx - a.genomic_start_tx;
        bLength = b.genomic_end_tx - b.genomic_start_tx;
        if (aLength > bLength) {
            return 1;
        }
        if (aLength < bLength) {
            return -1;
        }
        return 0;
    }

    //init attributes
    var ans = {};
    var exonList = [];
    var colorArr = [];  //initialized with colors when used in function
    var currSizeColor = 0;
    var interval = 10;

    //pushing all exons in different genes in the list
    for (var i = 0; i < result.genes.length; i++) {
        exonList.push.apply(exonList, result.genes[i].geneExons);
    }
    //sorting
    exonList = exonList.sort(compare);
    //getting first color
    ans[currSizeColor] = getcolorFromList(colorArr);

    //keep adding colors
    for (var i = 0; i < exonList.length; i++) {
        var currExonLength = exonList[i].genomic_end_tx - exonList[i].genomic_start_tx;
        if (currExonLength > currSizeColor + interval) {
            //new color
            currSizeColor = currExonLength;
            ans[currSizeColor] = getcolorFromList(colorArr);
        } else {
            //same color to last(same size)
            ans[currExonLength] = ans[currSizeColor];
        }
    }
    return ans;

}