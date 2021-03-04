class BetweenGenesInSpeciesDrawer {
    constructor() {

    }
    draw(results) {
        var names = results.names;
        var total = results.TranscriptSimilarity;
        results = results.resultMatrix;

        var html = "<table>";
        html = html + "<tr>";
        html = html + "<td>Transcripts</td>";

        for (var i = 0; i < results[0].length; i++) {
            html = html + "<td>" + names[i] + "</td>"
        }
        html = html + "</tr>";

        for (var i = 0; i < results.length; i++) {
            html = html + "<tr>";
            html = html + "<td>" + names[i] + "</td>";
            for (var j = 0; j < results[i].length; j++) {
                html = html + "<td>";
                if (i >= j) {
                    html = html + this.createCircle(results, i, j);
                }
                html = html + "</td>";
            }
            html = html + "</tr>"
        }
        html = html + "</table><br><br>Result:" + total;

        $('#graphVisualization').html(html);
    }
    createCircle(results, i, j) {
        //calculate circle
        var percent = Math.floor(results[i][j]);
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