class BetweenGenesDrawer {
    constructor() {

    }
    draw(results) {

        var speciesNames = results.species;
        var results = results.results;

        var html = "<table style='border: black solid 1px; padding: 5px; margin: 5px;'>";
        var titles = "<tr>"
        var values = "<tr>"
        for (var i = 0; i < results.length; i++) {
            if (isNaN(results[i])) {
                titles = titles + "<td>" + speciesNames[i] + "</td>";
                values = values + "<td>only one transcript</td>";
            } else {
                titles = titles + "<td style='border: black solid 1px;'>" + speciesNames[i] + "</td>";
                values = values + "<td style='border: black solid 1px;'>" + results[i] + "</td>";
            }
        }
        titles = titles + "</tr>";
        values = values + "</tr>";
        html = html + titles + values + "</table>";

        $('#graphVisualization').html(html);
    }
}