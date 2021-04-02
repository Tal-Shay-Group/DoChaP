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
        colorByLength = preferences.colorByLength ? true : undefined;
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
var originalColors =["#DACCFF", "#9B72FF","#B627FC",  "#DE3D3D", "#FF6262", "#f5b0cb", "#ffccd8",                
        "#CD923C", "#FFBB8F","#FD9900", "#ffb90f", "#ffd700", "#FFFC3B", "#FFF599", "#FFFED3", "#ccff00", "#20F876", "#63C37F","#5BAF2F",
          "#2D79FF", "#00ccff", "#7BEAD2","#beebe9"
    ];
var newColors =["#ff0000", "#bf0000", "#ff5757", "#b37979", "#bf6341", "#d9a693", "#ff8800", "#cc8d45", "#b39879", "#ffcc00", "#b29b3d", "#ffefad", "#d6e600", "#aaff00", "#4cb33d", "#aff2a5", "#00ff66", "#00d991", "#8bccb6", "#00ffee", "#00a3cc", "#9cd7e6", "#0088ff", "#458dcc", "#0044ff", "#a5a5f2", "#7c3db3", "#b800e6", "#f2a5ed", "#e64eb3", "#e5005c", "#f2a5c4"];

//selecting color from list (deterministic yet not in order)
function getcolorFromList(colorArr) {
    if (colorArr.length <= 1) {
        colorArr.push.apply(colorArr, newColors );
    }
        i = colorArr.length % 3;
        if (i == 0) {
            i = 0;
        } else if (i == 1) {
            i = colorArr.length - 1;
        } else if (i == 2) {
            i = colorArr.length / 2;
        }

    return colorArr.splice(i, 1)[0];
}

function getFirstColorFromList(colorArr) {
    if (colorArr.length <= 1) {
        colorArr.push.apply(colorArr, newColors );
    }
    return colorArr.splice(0, 1)[0];
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
