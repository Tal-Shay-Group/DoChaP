class BetweenTranscriptsDrawer {
    constructor() {

    }
    draw(results) {
        //write summary text
        //create graphs
        var names = results.names;
        var attributeCompare = results.attributeCompare;
        results = results.resultMatrix;
        var html = "Exons:<br><table>";
        html = html + "<tr>";
        html = html + "<td>" + names + "</td>";

        for (var i = 0; i < results[0].length; i++) {
            html = html + "<td style='text-align: center;'>E" + (i + 1) + "</td>"
        }
        html = html + "</tr>";

        for (var i = 0; i < results.length; i++) {
            html = html + "<tr>";
            html = html + "<td>E" + (i + 1) + "</td>";
            for (var j = 0; j < results[i].length; j++) {
                html = html + "<td>";
                html = html + this.createCircle(results, i, j) + "</td>";
            }
            html = html + "</tr>"
        }

        html = html + "</table><br><br>Result:" + attributeCompare[5].value;

        //attributes table
        html = html + "<table>";
        var titles = "<tr>"
        var values = "<tr>"
        for (var i = 0; i < attributeCompare.length; i++) {
            titles = titles + "<td style='width: 80px; height: 80px;'>" + attributeCompare[i].title + "</td>";
            values = values + "<td>" + attributeCompare[i].value + "</td>";
        }
        titles = titles + "</tr>";
        values = values + "</tr>";
        html = html + titles + values + "</table>";
        $('#graphVisualization').html(html);
    }

    createCircle(results, i, j) {
        //calculate circle
        var percent = Math.floor(results[i][j] * 100);
        var radiusSize = percent / 2 + 20;
        var style = {
            "background": "#f00",
            "width": radiusSize + "px",
            "height": radiusSize + "px",
            "border-radius": "50%",
            "text-align": "center",
            "vertical-align": "middle",
            "line-height": radiusSize + "px",
            "margin": "auto"
        }

        var circle = $("<div>").css(style).text(percent);
        return circle.prop('outerHTML') + "</td>";
    }
}