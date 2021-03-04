class BetweenGenesInSpeciesComparator {
    constructor() {

    }

    compare(firstElement, secondElement, weights) {
        var transcripts1 = firstElement.transcripts;
        var transcripts2 = secondElement.transcripts;
        var compartor = new BetweenTranscriptsComparator();
        var results = [];
        var names = [];
        var sum = 0;
        var count = 0;
        for (var i = 0; i < transcripts1.length; i++) {
            results[i] = [];
            names.push(transcripts1[i].name);
            for (var j = 0; j < transcripts2.length; j++) {
                var percent = compartor.compare(transcripts1[i], transcripts2[j], weights)['attributeCompare'][5]['value']
                results[i][j] = percent;
                if (i > j) {
                    count = count + 1;
                    sum = sum + percent;
                }

            }
        }
        return {
            "resultMatrix": results,
            "TranscriptSimilarity": sum / count,
            "names": names
        };
    }

}