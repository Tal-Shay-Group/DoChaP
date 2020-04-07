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
        colorArr.push.apply(colorArr, ["#DACCFF", "#BBABF3", "#B627FC", "#DE3D3D", "#FF6262", "#f5b0cb", "#ffccd8",

        "#deb881", "#c8965d", "#FD9900", "#ffb90f", "#ffd700", "#FFFC3B", "#FFF599", "#FFFED3", "#d1d797", "#ccff00", "#20F876", "#63C37F",
        "#beebe9", "#00ccff", "#7BEAD2", "#180CF5"
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

function getColorForLength(result) {
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

    var ans = {};
    var exonList = [];
    for (var i = 0; i < result.genes.length; i++) {
        exonList.push.apply(exonList, result.genes[i].geneExons);
    }
    exonList = exonList.sort(compare);
    var colorArr = [];  //initialized with colors when used in function
    var currSizeColor = 0;
    var interval = 10;
    ans[currSizeColor] = getcolorFromList(colorArr);
    for (var i = 0; i < exonList.length; i++) {
        var currExonLength = exonList[i].genomic_end_tx - exonList[i].genomic_start_tx;
        if (currExonLength > currSizeColor + interval) {
            currSizeColor = currExonLength;
            ans[currSizeColor] = getcolorFromList(colorArr);
        } else {
            ans[currExonLength] = ans[currSizeColor];
        }
    }
    return ans;

}