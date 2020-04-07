class Domain {
    constructor(dbDomain, proteinStart = 0) {
        this.start = dbDomain.nuc_start - proteinStart;
        this.end = dbDomain.nuc_end - proteinStart;
        this.AAstart = dbDomain.AA_start;
        this.AAend = dbDomain.AA_end;
        this.name = dbDomain.domainType.name;
        this.typeID = dbDomain.domainType.type_id;
        this.overlap = false;
        this.showText = true;
        this.source = dbDomain.ext_id;
    }

    //compare function. used when drawing small domains before big ones so they won't crash
    static compare(a, b) {
        var aLength = a.end - a.start;
        var bLength = b.end - b.start;
        if (aLength > bLength) {
            return -1;
        }
        if (aLength < bLength) {
            return 1;
        }
        return 0;
    }


    draw(context, coordinatesWidth, startHeight, isFullDraw, exons) {
        //position
        var pos = this.position(coordinatesWidth, startHeight);
        var domainWidth = pos.domainWidth;
        var domainX = pos.domainX;
        var domainHeight = pos.domainHeight;
        var domainY = pos.domainY;
        var shapeID = this.typeID % 4; //currently its by type ID 

        //choosing draw settings. if undefined it is background white so half transparent domain will look better 
        if (isFullDraw == false) {
            context.fillStyle = "white";
            var domainName = "";
            var overlap = false;
            var domainText = false;
        } else {
            var gradient = this.getGradientForDomain(context, domainX, domainX + domainWidth, startHeight, exons);
            context.fillStyle = gradient;
            var domainName = this.name.replace(/_/g, "\n").replace(/ /g, "\n");
            var overlap = this.overlap;
            var domainText = this.showText;
        }

        //choose by shape
        context.beginPath();
        if (shapeID == 0 || true) {
            context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, domainWidth / 2, domainHeight / 2, 0, 0, 2 * Math.PI);
        } else if (shapeID == 1) {
            context.moveTo(domainX, domainY);
            context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
            context.lineTo(domainX + domainWidth, domainY);
        } else if (shapeID == 2) {
            context.moveTo(domainX, domainY);
            context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
            context.lineTo(domainX + domainWidth, domainY);
        } else if (shapeID == 3) {
            context.moveTo(domainX + domainWidth / 2, domainY);
            context.lineTo(domainX + domainWidth, domainY + domainHeight / 2);
            context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
            context.lineTo(domainX, domainY + domainHeight / 2);
        }
        context.closePath();

        context.save();
        context.translate(0, 0);
        context.shadowColor = "#898";
        context.shadowBlur = 6;
        context.shadowOffsetX = 2;
        context.shadowOffsetY = 2;
        //fill by overlap choice -not overlapping since domainGroup exists so it is not in use
        if (overlap) {
            context.globalAlpha = 0.3;
            context.fill();
            context.globalAlpha = 1;
        } else {
            context.fill();
        }

        context.restore();
        //border
        context.strokeStyle = "grey";
        context.lineWidth = 2;
        context.stroke();

        //show text if needed in diagonal
        if (domainText) {
            context.save();
            context.translate(domainX + domainWidth / 2, domainY + domainHeight + 8);
            context.rotate(Math.PI / 16);
            var lineheight = 15;
            var lines = domainName.split('\n');
            context.fillStyle = "black"; //for text
            context.font = "20px Calibri"; //bold 
            context.shadowColor = "#898";
            context.shadowBlur = 4;
            context.shadowOffsetX = 2;
            context.shadowOffsetY = 3;
            //we must draw each line saperatly because canvas can't draw '\n'
            context.textAlign = "left";
            for (var i = 0; i < lines.length; i++) {
                context.fillText(lines[i], 0, 10 + (i * lineheight));
            }
            context.restore();
        }


    }

    //calculations of gradient color
    getGradientForDomain(context, start, end, height, exons) { //exons are absolute position for this to work
        var gradient = context.createLinearGradient(start, height, end, height); //contextP only for domains now
        var whiteLineRadius = 10;
        var normalizer = 1 / (this.end - this.start);
        for (var i = 0; i < exons.length; i++) {
            var exonStart = exons[i].transcriptViewStart;
            var exonEnd = exons[i].transcriptViewEnd;
            if (exonStart <= this.start && this.start <= exonEnd && exonStart <= this.end && this.end <= exonEnd) {
                //no junctions so only one color
                return exons[i].color;
            } else if (exonStart <= this.start && this.start <= exonEnd) {
                //the starting color for the domain
                gradient.addColorStop(0, exons[i].color);
                var position = Math.max(0, (exonEnd - this.start - whiteLineRadius) * normalizer);
                gradient.addColorStop(position, exons[i].color);
                //white line (if wanted)
                gradient.addColorStop((exonEnd - this.start) * normalizer, "white");
            } else if (exonStart <= this.end && this.end <= exonEnd) {
                //ending color for domain
                var position = Math.min(1, (exonStart - this.start + whiteLineRadius) * normalizer);
                gradient.addColorStop(position, exons[i].color);
                gradient.addColorStop(1, exons[i].color);
            } else if (this.start <= exonStart && exonEnd <= this.end) {
                //color for exon in the middle (not starting or finishing)

                //white lines (if wanted)
                gradient.addColorStop((exonStart - this.start) * normalizer, "white");
                gradient.addColorStop((exonEnd - this.start) * normalizer, "white");

                //main coloring
                var position1 = Math.min(1, (exonStart - this.start + whiteLineRadius) * normalizer);
                var position2 = Math.max(0, (exonEnd - this.start - whiteLineRadius) * normalizer);
                gradient.addColorStop(position1, exons[i].color);
                gradient.addColorStop(position2, exons[i].color);
            }
        }

        return gradient;
    }

    /**
     * 
     * @param {arr of domains} domains - it edits (inplace) the overlap attributes in domains
     *  if they overlap in positions (one or more overlaps means true, otherwise false)
     * note: it also sorts domains by start position
     */
    static findOverlaps(domains) {
        function compare(a, b) {
            if (a.start < b.start) {
                return -1;
            }
            if (a.start > b.start) {
                return 1;
            }
            if (a.start == b.start && a.end < b.end) {
                return 1;
            }
            return 0;
        }
        domains.sort(compare);
        for (var i = 0; i < domains.length; i++) {
            if (domains[i].overlap == true) { //already known to overlap
                continue;
            }
            for (var j = i + 1; j < domains.length; j++) {
                if (domains[i].end >= domains[j].start) { //overlap
                    domains[i].overlap = true;
                    domains[j].overlap = true;
                } else {
                    break; //if we are not overlapping then further domains will not too;\
                }
            }
        }
    }

    tooltip(coordinatesWidth, startHeight) {
        //position
        var pos = this.position(coordinatesWidth, startHeight);
        var domainWidth = pos.domainWidth;
        var domainX = pos.domainX;
        var domainHeight = pos.domainHeight;
        var domainY = pos.domainY;

        //for tooltip text
        var name = this.name;
        var start = this.AAstart;
        var end = this.AAend;
        var length = end - start;
        var source = this.source;
        var sourceName = "";
        if (source == undefined) {
            sourceName = "Source";
            source = "unknown";
        }
        if (source.substring(0, 5) == 'smart') {
            sourceName = "Smart";
        }
        if (source.substring(0, 4) == 'pfam') {
            sourceName = "Pfam";
        }
        if (source.substring(0, 2) == 'cd' || source.substring(0, 2) == 'cl') {
            sourceName = "CDD";
        }
        if (source.substring(0, 4) == 'TIGR') {
            sourceName = "Tigr";
        }
        var text = "<u>" + name + "</u><br> Positions: " + start + "-" + end + "<br>Length: " + length + "<br>" + sourceName + ": <a href='" + Species.getURLfor(source) + "' target='_blank' >" + source + "</a>";
        //var text=name;
        return [domainX, domainY, domainWidth, domainHeight, text, undefined];
    }


    //when seeing overlapping domains it choses which one to show text to
    /**
     * 
     * @param {arr of domains} domains - we iterate through domain and edit (inplace)
     * the showText attribute to be true or false. If domains are close and overlapping
     * then we only show some domains. (the left one I think...). 
     * note: if there is an someoverlapping domains where one does not show text then
     * the other can show text even if it is not the left one. 
     */
    static showNameOfDomains(domains) {
        for (var i = 0; i < domains.length; i++) {
            for (var j = 0; j < domains.length; j++) {
                if (i == j) {
                    continue;
                }
                if (!(domains[i].showText && domains[j].showText)) { //one of them is not shown
                    continue;
                }
                if (domains[i].start <= domains[j].start && domains[j].end <= domains[i].end) {
                    domains[i].showText = false;
                } else if (domains[i].start <= domains[j].start && domains[i].end <= domains[j].end && domains[j].start < domains[i].end) {
                    domains[i].showText = false;
                }
            }
        }
    }
    /*
    some domain overlap so we group them into the DomainGroup object
    */
    static groupDomains(domains) {
        //sorting is it correct (?)
        function compare(a, b) {
            if (a.start < b.start) {
                return -1;
            }
            if (a.start > b.start) {
                return 1;
            }
            if (a.start == b.start && a.end < b.end) {
                return 1;
            }
            if (a.start == b.start && a.end > b.end) {
                return -1;
            }
            return 0;
        }
        domains.sort(compare);

        //finding overlaps
        var finalDomains = [];
        var tempDomainArr = [];
        var currCoordinate = -1;
        for (var i = 0; i < domains.length; i++) {
            if (domains[i].end <= currCoordinate || domains[i].start <= currCoordinate) {
                //case may overlap
                tempDomainArr.push(domains[i]);
                currCoordinate = Math.max(currCoordinate, domains[i].end);
            } else {
                //case not overlap
                if (tempDomainArr.length == 1) {
                    finalDomains.push(tempDomainArr[0]);
                } else if (tempDomainArr.length > 1) {
                    finalDomains.push(new DomainGroup(tempDomainArr));
                }
                tempDomainArr = [domains[i]];
                currCoordinate = domains[i].end;

            }
        }

        //if something is left in the tempDomainArr we add them
        if (tempDomainArr.length == 1) {
            finalDomains.push(tempDomainArr[0]);
        } else if (tempDomainArr.length > 1) {
            finalDomains.push(new DomainGroup(tempDomainArr));
        }

        return finalDomains;
    }
    position(coordinatesWidth, startHeight) {
        var pos = new Object();
        pos.domainWidth = (this.end - this.start) * coordinatesWidth;
        pos.domainX = this.start * coordinatesWidth;
        pos.domainHeight = 45;
        pos.domainY = startHeight - pos.domainHeight / 2;
        return pos;
    }

    drawExtend(context, coordinatesWidth, startHeight, isFullDraw, exons, domainHeight, domainY, domainX, domainWidth) {
        //position
        var pos = this.position(coordinatesWidth, startHeight);
        var domainWidth = pos.domainWidth;
        var domainX = pos.domainX;
        //var domainHeight =pos.domainHeight;
        //var domainY =pos.domainY;
        var shapeID = this.typeID % 4; //currently its by type ID 

        //choosing draw settings. if undefined it is background white so half transparent domain will look better 
        if (isFullDraw == false) {
            context.fillStyle = "white";
            var domainName = "";
            var overlap = false;
            var domainText = false;
        } else {
            var gradient = this.getGradientForDomain(context, domainX, domainX + domainWidth, startHeight, exons);
            context.fillStyle = gradient;
            var domainName = this.name.replace(/_/g, "\n").replace(/ /g, "\n");
            var overlap = this.overlap;
            var domainText = this.showText;
        }

        //choose by shape
        context.beginPath();
        if (shapeID == 0 || true) {
            context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, domainWidth / 2, domainHeight / 2, 0, 0, 2 * Math.PI);
        } else if (shapeID == 1) {
            context.moveTo(domainX, domainY);
            context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
            context.lineTo(domainX + domainWidth, domainY);
        } else if (shapeID == 2) {
            context.moveTo(domainX, domainY);
            context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
            context.lineTo(domainX + domainWidth, domainY);
        } else if (shapeID == 3) {
            context.moveTo(domainX + domainWidth / 2, domainY);
            context.lineTo(domainX + domainWidth, domainY + domainHeight / 2);
            context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
            context.lineTo(domainX, domainY + domainHeight / 2);
        }
        context.closePath();

        //fill by overlap choice
        if (false /*overlap*/ ) {
            context.globalAlpha = 0.3;
            context.fill();
            context.globalAlpha = 1;
        } else {
            context.fill();
        }

        //border
        context.strokeStyle = "grey";
        context.lineWidth = 1;
        context.stroke();

        //show text if needed in diagonal
        if (false /*domainText*/ ) {
            context.save();
            context.translate(domainX + domainWidth / 2, domainY + domainHeight + 8);
            context.rotate(Math.PI / 16);
            var lineheight = 15;
            var lines = domainName.split('\n');
            context.fillStyle = "black"; //for text
            context.font = "20px Calibri"; //bold 

            //we must draw each line saperatly because canvas can't draw '\n'
            context.textAlign = "left";
            for (var i = 0; i < lines.length; i++) {
                context.fillText(lines[i], 0, 10 + (i * lineheight));
            }
            context.restore();
        }


    }

    proteinExtendTooltip(coordinatesWidth, startHeight, domainHeight, domainY) {
        var regulartooltip = this.tooltip(coordinatesWidth, startHeight);
        regulartooltip[1] = domainY;
        regulartooltip[3] = domainHeight;
        return [regulartooltip]; //saved in array because we take arrays of domains when it comes from domain group. here is a case where domain like a domainGroup of size 1
    }

    static domainClick(tooltipManager,event) {
        var showTextValues = Transcript.showText(event, tooltipManager);
        if (showTextValues[0]) {
            if (showTextValues[2] == 'click' && tooltipManager[event.target.id + "object"] != undefined) {
                tooltipManager[event.target.id + "object"].proteinExtendView = !tooltipManager[event.target.id + "object"].proteinExtendView;
            }

        }
    }

}