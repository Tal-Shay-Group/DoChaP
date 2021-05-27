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
 * selecting how much is for skip. depends on proportions between the canvas size and protein size
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
// var newColors =['#ff0000', '#bf0000', '#ff5757', '#b37979', '#bf6341', '#d9a693', '#ff8800',
//           '#cc8d45', '#b39879', '#ffcc00', '#b29b3d', '#ffefad', '#d6e600', '#aaff00',
//           '#4cb33d', '#aff2a5', '#00ff66', '#00d991', '#8bccb6', '#00ffee', '#00a3cc',
//           '#9cd7e6', '#0088ff', '#458dcc', '#0044ff', '#a5a5f2', '#7c3db3', '#b800e6',
//           '#f2a5ed', '#e64eb3'
//     ];
// var newColors =["#ff0000", "#bf0000", "#ff5757", "#b37979", "#bf6341", "#d9a693", "#ff8800", "#cc8d45", "#b39879", "#ffcc00", "#b29b3d", "#ffefad", "#d6e600", "#aaff00", "#4cb33d", "#aff2a5", "#00ff66", "#00d991", "#8bccb6", "#00ffee", "#00a3cc", "#9cd7e6", "#0088ff", "#458dcc", "#0044ff", "#a5a5f2", "#7c3db3", "#b800e6", "#f2a5ed", "#e64eb3", "#e5005c", "#f2a5c4"];
var newColors = ["#FF4A46", "#1BE177", "#00CCFF", "#A30059", "#FFB500", "#006FA6", "#4FC601", "#FFDBE5",
           "#D16100", "#00C2A0", "#A079BF", "#C0B9B2", "#CC0744", "#549E79", "#B79762", "#B903AA", "#00846F",
           "#FF90C9", "#0AA6D8",   "#F4ABAA", "#A3F3AB", "#00C6C8",
           "#EA8B66","#BEC459", "#AA5199",  "#0089A3", "#EEC3FF", "#8FB0FF",
           "#004D43", "#F4D749", "#997D87", "#3B5DFF", "#FF2F80",
           "#6B7900", "#FFAA92", "#A1C299",
           "#885578", "#B77B68", "#FAD09F", "#456D75", "#FF8A9A", "#0086ED", "#D157A0", "#00A6AA",
           "#B4A8BD", "#FF913F", "#636375", "#A3C8C9", "#00FECF", "#B05B6F", "#3B9700", "#C8A1A1",
           "#7900D7", "#8CD0FF", "#A77500", "#6367A9", "#6B002C", "#9B9700", "#D790FF", "#63FFAC",
           "#72418F", "#FFF69F", "#BC23FF",
           "#99ADC0", "#922329", "#C2FFED", "#CB7E98", "#A4E804", "#324E72", "#6A3A4C", "#83AB58",
           "#D1F7CE", "#004B28", "#C8D0F6", "#BF5650", "#66796D", "#FF1A59", "#8ADBB4", "#C895C5",
           "#FF6832", "#66E1D3", "#D0AC94", "#7ED379", "#7A7BFF", "#D68E01", "#78AFA1", "#FEB2C6",
           "#75797C", "#837393", "#943A4D", "#B5F4FF", "#D2DCD5", "#9556BD", "#6A714A", "#02525F",
           "#5EBCD1", "#3D4F44", "#02684E", "#962B75", "#8D8546", "#9695C5",
           "#E773CE", "#D86A78", "#3E89BE", "#CA834E", "#518A87", "#5B113C", "#55813B", "#00005F",
           "#A97399", "#4B8160", "#59738A", "#FF5DA7", "#F7C9BF", "#6B94AA", "#51A058", "#A45B02",
           "#E20027", "#E7AB63", "#4C6001", "#9C6966", "#64547B", "#006A66", "#0045D2",
           "#006C31", "#7C6571", "#9FB2A4", "#00D891", "#15A08A", "#BC65E9", "#C6DC99", "#671190",
           "#6B3A64", "#F5E1FF", "#FFA0F2", "#CCAA35", "#374527", "#8BB400", "#797868", "#C6005A",
           "#C86240", "#29607C", "#7D5A44", "#CCB87C", "#B88183", "#B5D6C3", "#A38469", "#9F94F0",
           "#A74571", "#B894A6", "#71BB8C", "#00B433", "#789EC9", "#E4FFFC", "#BCB1E5", "#008941",
           "#76912F", "#0060CD", "#D20096", "#494B5A", "#A88C85",  "#958A9F", "#BDC9D2", "#9FA064", "#BE4700", "#658188", "#83A485", "#47675D",
           "#DFFB71", "#868E7E", "#98D058", "#6C8F7D", "#D7BFC2", "#3C3E6E", "#D83D66", "#2F5D9B",
           "#6C5E46", "#D25B88", "#5B656C", "#00B57F", "#545C46", "#866097", "#365D25", "#252F99",
           "#674E60", "#FC009C", "#92896B"];
// var newColors = ["#ff0000", "#00ff00", "#0000ff"];
//selecting color from list (deterministic yet not in order)
function getcolorFromList(colorArr) {
    if (colorArr.length <= 1) {
        colorArr.push.apply(colorArr, newColors );
    }
        // i = colorArr.length % 3;
        // if (i == 0) {
        //     i = 0;
        // } else if (i == 1) {
        //     i = colorArr.length - 1;
        // } else if (i == 2) {
        //     i = colorArr.length / 2;
        // }
    i=0;
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
