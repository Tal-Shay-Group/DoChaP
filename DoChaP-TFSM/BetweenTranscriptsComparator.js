class BetweenTranscriptsComparator {
    constructor() {

    }

    compare(firstElement, secondElement, weights) {
        var analyzed1 = this.analyzeTranscript(firstElement);
        var analyzed2 = this.analyzeTranscript(secondElement);

        //attribute comparison
        var attributeCompare = [];
        var TXStartChange = Math.abs(analyzed1.TXStart - analyzed2.TXStart);
        var TXEndChange = Math.abs(analyzed1.TXEnd - analyzed2.TXEnd);
        var CDSStartChange = Math.abs(analyzed1.CDSStart - analyzed2.CDSStart);
        var CDSEndChange = Math.abs(analyzed1.CDSEnd - analyzed2.CDSEnd);
        attributeCompare.push({
            "title": "TX Start Difference",
            "value": TXStartChange
        });
        attributeCompare.push({
            "title": "TX End Difference",
            "value": TXEndChange
        });
        attributeCompare.push({
            "title": "CDS Start Difference",
            "value": CDSStartChange
        });
        attributeCompare.push({
            "title": "CDS End Difference",
            "value": CDSEndChange
        });

        //domain similarity
        var commonDomains = 0;
        for (var i = 0; i < analyzed1.domainTypes.length; i++) {
            for (var j = 0; j < analyzed2.domainTypes.length; j++) {
                if (analyzed1.domainTypes[i] == analyzed2.domainTypes[j]) {
                    commonDomains = commonDomains + 1;
                }
            }
        }
        var allDomains = analyzed1.domainTypes.length + analyzed2.domainTypes.length - commonDomains;
        var domainTypeSimilarity = commonDomains / allDomains;
        attributeCompare.push({
            "title": "Domain Similarity",
            "value": (domainTypeSimilarity * 100) + "%"
        });


        //exon similarity
        var resultMatrix = this.getExonSimilarity(analyzed1, analyzed2, weights);
        var totalExonSimilarity = this.getTotalExonSimilarity(resultMatrix);
        attributeCompare.push({
            "title": "Exon Similarity",
            "value": totalExonSimilarity
        });

        //names
        var names = analyzed1.name + "\\" + analyzed2.name
        return {
            "resultMatrix": resultMatrix,
            "attributeCompare": attributeCompare,
            'names': names
        };

    }

    analyzeTranscript(element) {
        var features = {};
        features.name = element.name;
        features.CDSStart = element.cds_start;
        features.CDSEnd = element.cds_end;
        features.TXStart = element.tx_start;
        features.TXEnd = element.tx_end;

        features.domainTypes = [];
        features.domainNames = {};
        var domains = element.domains;
        for (var i = 0; i < domains.length; i++) {
            if (!features.domainTypes.includes(domains[i].type_id)) {
                features.domainTypes.push(domains[i].type_id);
                features.domainNames[domains[i].type_id] = domains[i].domainType.name;

            }
        }

        //mapping domains to exons
        var spliceInDomains = element.spliceInDomains;
        var exon_order_in_transcript = {};
        // for (var i = 0; i < spliceInDomains.length; i++) {
        //     var position = spliceInDomains[i].exon_order_in_transcript;
        //     if (exon_order_in_transcript[position] == undefined) {
        //         exon_order_in_transcript[position] = [];
        //     }
        //     exon_order_in_transcript[position].push(spliceInDomains[i].type_id);
        // }

        //mapping complete domains
        for (var i = 0; i < domains.length; i++) {
            
            var position = this.getExonPosition(element.transcriptExons,domains[i]);
            //if more than one exon then we have it splice in domains
            if(position==-1){
                continue;
            }
            if (exon_order_in_transcript[position] == undefined) {
                exon_order_in_transcript[position] = [];
            }
            exon_order_in_transcript[position].push(domains[i].type_id);
        }

        //insert to exons
        features.transcriptExons = element.transcriptExons;
        for (var i = 0; i < features.transcriptExons.length; i++) {
            var position = features.transcriptExons[i].order_in_transcript;
            features.transcriptExons[i].domainTypes = exon_order_in_transcript[position];
            if (features.transcriptExons[i].domainTypes == undefined) {
                features.transcriptExons[i].domainTypes = [];
            }
        }

        return features; //element.exon_count;
    }
    getExonSimilarity(firstElement, secondElement, weights) {
        let exons1 = firstElement.transcriptExons.sort(this.exonOrder);
        let exons2 = secondElement.transcriptExons.sort(this.exonOrder);
        let results = [];
        let weightSum = weights[0] + weights[1] + weights[2];

        for (var i = 0; i < exons1.length; i++) {
            results[i] = [];
            for (var j = 0; j < exons2.length; j++) {

                var A = this.getCoordinatesMeasure(exons1[i].genomic_start_tx, exons1[i].genomic_end_tx, exons2[j].genomic_start_tx,
                    exons2[j].genomic_end_tx);

                var B = this.getLengthMeasure(exons1[i].abs_start_CDS, exons1[i].abs_end_CDS, exons2[j].abs_start_CDS,
                    exons2[j].abs_end_CDS);


                var C = this.getDomainMeasure(exons1[i].domainTypes, exons2[j].domainTypes);

                if (A == 1) {
                    results[i][j] = (1 * weights[0] + 1 * weights[1] + 1 * weights[2]) / weightSum;
                } else {
                    results[i][j] = (A * weights[0] + B * weights[1] + C * weights[2]) / weightSum;
                }

            }
        }
        return results;

    }

    exonOrder(a, b) {
        if (a.genomic_start_tx != b.genomic_start_tx) {
            return a.genomic_start_tx - b.genomic_start_tx;
        }
        return a.genomic_end_tx - b.genomic_end_tx;
    }

    getCoordinatesMeasure(start1, end1, start2, end2) {
        var jointArea = Math.min(end1, end2) - Math.max(start1, start2);
        var allArea = Math.max(end1, end2) - Math.min(start1, start2);
        if (jointArea < 0) {
            jointArea = 0;
        }
        return jointArea / allArea;
    }

    getLengthMeasure(start1, end1, start2, end2) {
        var length1 = end1 - start1;
        var length2 = end2 - start2;
        if (length1 == length2 && length1 != 0) {
            return 1;
        } else {
            return 0;
        }

    }

    getDomainMeasure(arr1, arr2) {
        if (arr1.length == 0 || arr2.length == 0) {
            return 0;
        }
        var tempArr2 = arr2.slice() //create copy
        var common = 0;
        for (var i = 0; i < arr1.length; i++) {
            if (tempArr2.includes(arr1[i])) {
                common = common + 1;
                tempArr2.splice(tempArr2.indexOf(arr1[i]), 1); //delete element once
            }
        }
        return common / (arr1.length + arr2.length - common); //union after deleting duplicates from array2
    }

    getTotalExonSimilarity(resultMatrix) {
        var totalExons = resultMatrix.length + resultMatrix[0].length;
        var sum = 0;
        for (var i = 0; i < resultMatrix.length; i++) {
            sum = sum + Math.max(...resultMatrix[i]);
        }

        for (var j = 0; j < resultMatrix[0].length; j++) {
            var colVal = [];
            for (var i = 0; i < resultMatrix.length; i++) {
                colVal.push(resultMatrix[i][j]);
            }
            sum = sum + Math.max(...colVal);
        }
        return (sum * 100) / (totalExons);
    }

    getExonPosition(exons,domain){
        var domainStart = domain.nuc_start;
        var exon = undefined;
        for (var i=0; i<exons.length;i++){
            if(exons[i].abs_start_CDS <= domainStart && domainStart <= exons[i].abs_end_CDS){
                exon=exons[i];
                break;
            }
        }
        if(domain.nuc_end<=exon.abs_end_CDS){
            return exon.order_in_transcript;
        }
        else {
            return -1;
        }
        
    }



}