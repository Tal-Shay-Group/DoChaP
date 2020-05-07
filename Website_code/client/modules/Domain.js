/**
 * Domains are main part of the protein view.
 * These are the circles that are representing protein domains.
 * 
 */
class Domain {
    /**
     * 
     * @param {domain row from db} dbDomain - the domain row from db
     * @param {int} proteinStart - location to start drawing from in canvas, nuc units.
     */
    constructor(dbDomain, proteinStart = 0) {
        //calculatiing attribute 
        this.start = dbDomain.nuc_start - proteinStart; //nuc units
        this.end = dbDomain.nuc_end - proteinStart; //nuc units
        this.AAstart = dbDomain.AA_start; //aa units
        this.AAend = dbDomain.AA_end; //aa units
        this.name = dbDomain.domainType.name;
        this.typeID = dbDomain.domainType.type_id;
        this.source = dbDomain.ext_id;

        //default view attributes
        this.overlap = false;
        this.showText = true;
    }

    /**
     * compare function. used when drawing small domains before big ones so they won't collide
     * @param {Domain} a - first of two domains to compare
     * @param {Domain} b - second of two domains to compare
     */
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

    /**
     * 
     * @param {canvasContext} context - context to draw on
     * @param {double} coordinatesWidth - the measure of scaling used
     * @param {int} startHeight - size between the top of the canvas to the top of the domain
     * @param {boolean} isFullDraw - full draw is regular draw 
     * and not full draw is just a white circle needed before drawing for opacity aesthetics
     * @param {array of Exon} exons 
     */
    draw(context, coordinatesWidth, startHeight, isFullDraw, exons) {
        //get calculated position
        var pos = this.position(coordinatesWidth, startHeight);
        var domainWidth = pos.domainWidth;
        var domainX = pos.domainX;
        var domainHeight = pos.domainHeight;
        var domainY = pos.domainY;
        // var shapeID = this.typeID % 4; //currently its by type ID 

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
        context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, domainWidth / 2, domainHeight / 2, 0, 0, 2 * Math.PI);
        // if (shapeID == 0) {
        //     context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, domainWidth / 2, domainHeight / 2, 0, 0, 2 * Math.PI);
        // } else if (shapeID == 1) {
        //     context.moveTo(domainX, domainY);
        //     context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
        //     context.lineTo(domainX + domainWidth, domainY);
        // } else if (shapeID == 2) {
        //     context.moveTo(domainX, domainY);
        //     context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
        //     context.lineTo(domainX + domainWidth, domainY);
        // } else if (shapeID == 3) {
        //     context.moveTo(domainX + domainWidth / 2, domainY);
        //     context.lineTo(domainX + domainWidth, domainY + domainHeight / 2);
        //     context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
        //     context.lineTo(domainX, domainY + domainHeight / 2);
        // }
        context.closePath();

        //adding shadow below
        context.save();
        context.translate(0, 0);
        context.shadowColor = "#898";
        context.shadowBlur = 6;
        context.shadowOffsetX = 2;
        context.shadowOffsetY = 2;

        //fill by overlap choice
        if (overlap) {
            context.globalAlpha = 0.3;
            context.fill();
            context.globalAlpha = 1;
        } else {
            context.fill();
        }

        //end shadows
        context.restore();

        //border
        context.strokeStyle = "grey";
        context.lineWidth = 2;
        context.stroke();

        //if needed shows text in diagonal
        if (domainText) {

            //rotate
            context.save();
            context.translate(domainX + domainWidth / 2, domainY + domainHeight + 8);
            context.rotate(Math.PI / 16);

            //text options
            var lineheight = 15;
            var lines = domainName.split('\n');
            context.fillStyle = "black";
            context.font = "20px Calibri";

            //text shadow
            context.shadowColor = "#898";
            context.shadowBlur = 4;
            context.shadowOffsetX = 2;
            context.shadowOffsetY = 3;

            //we must draw each line saperatly because canvas can't draw '\n'
            context.textAlign = "left";
            for (var i = 0; i < lines.length; i++) {
                context.fillText(lines[i], 0, 10 + (i * lineheight));
            }

            //finish rotate and shadow
            context.restore();
        }


    }

    //calculations of gradient color
    /**
     * 
     * @param {canvas context} context - where we draw
     * @param {double} start - X position of canvas of domain start
     * @param {double} end  - X position of canvas of domain end
     * @param {int} height  - to know from what height to start color
     * @param {array of Exon} exons - exons have color needed for gradient and position for color
     */
    getGradientForDomain(context, start, end, height, exons) { //exons are absolute position for this to work
        //create gradient
        var gradient = context.createLinearGradient(start, height, end, height);
        var whiteLineRadius = 10;
        var normalizer = 1 / (this.end - this.start); //normalizer for scaling changes in color on axis proportion to domain length

        //iterating through exons for start coloring
        for (var i = 0; i < exons.length; i++) {
            var exonStart = exons[i].transcriptViewStart;
            var exonEnd = exons[i].transcriptViewEnd;

            //no junctions so only one color
            if (exonStart <= this.start && this.start <= exonEnd && exonStart <= this.end && this.end <= exonEnd) {

                return exons[i].color;

                //the starting color for the domain
            } else if (exonStart <= this.start && this.start <= exonEnd) {
                gradient.addColorStop(0, exons[i].color);
                var position = Math.max(0, (exonEnd - this.start - whiteLineRadius) * normalizer);
                gradient.addColorStop(position, exons[i].color);
                //white border for splice junction
                gradient.addColorStop((exonEnd - this.start) * normalizer, "white");

                //ending color for domain
            } else if (exonStart <= this.end && this.end <= exonEnd) {
                var position = Math.min(1, (exonStart - this.start + whiteLineRadius) * normalizer);
                gradient.addColorStop(position, exons[i].color);
                gradient.addColorStop(1, exons[i].color);

                //color for exon in the middle (not starting or finishing)
            } else if (this.start <= exonStart && exonEnd <= this.end) {

                //white border for splice junction
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
        //sort by order in axis.
        function compare(a, b) {
            if (a.start < b.start) {
                return -1;
            }
            if (a.start > b.start) {
                return 1;
            }
            return b.end - a.end;
        }
        domains.sort(compare);


        for (var i = 0; i < domains.length; i++) {


            if (domains[i].overlap == true) { //already known to overlap so we skip to next domain
                continue;
            }

            for (var j = i + 1; j < domains.length; j++) {
                if (domains[i].end >= domains[j].start) { //overlap
                    domains[i].overlap = true;
                    domains[j].overlap = true;
                } else {
                    break; //if we are not overlapping then further domains will not too;
                }
            }
        }
    }

    /**
     * creating tooltip info for this domain
     * @param {*} coordinatesWidth - needed for position calculations, check position for details
     * @param {*} startHeight  - needed for position calculations, check position for details
     */
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

        //finding sourcename
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


        var text = "<u>" + name + "</u><br> Positions: " + start + "-" + end + "<br>Length: " + length + "aa<br>" + sourceName + ": <a href='" + Species.getURLfor(source) + "' target='_blank' >" + source + "</a>";
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

    /**
     * some domain overlap so we group *all* of them into the DomainGroup object
     * @param {array of Domain} domains
     */
    static groupAllOverlappingDomains(domains) {
        //sorting is it correct
        function compare(a, b) {
            if (a.start < b.start) {
                return -1;
            }
            if (a.start > b.start) {
                return 1;
            }
            return b.end - a.end;
        }
        domains.sort(compare);

        //finding overlaps
        var finalDomains = [];
        var tempDomainArr = [];
        var currCoordinate = -1;
        for (var i = 0; i < domains.length; i++) {

            //case may overlap
            if (domains[i].end <= currCoordinate || domains[i].start <= currCoordinate) {
                tempDomainArr.push(domains[i]);
                currCoordinate = Math.max(currCoordinate, domains[i].end);
            
            //case not overlap
            } else {
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

    /**
     * find x,y,height, width positions of domain in canvas 
     * 
     * @param {double} coordinatesWidth - scaling parameter for converting nuc sizes to pixel sizes
     * @param {int} startHeight - size between the top of the canvas to the top of the domain
     */
    position(coordinatesWidth, startHeight) {
        var pos = new Object();
        pos.domainWidth = (this.end - this.start) * coordinatesWidth;
        pos.domainX = this.start * coordinatesWidth;
        pos.domainHeight = 45;
        pos.domainY = startHeight - pos.domainHeight / 2;
        return pos;
    }

/**
 * our fourth view when clicking on domain is that we see the domains that overlap one below another
 * @param {canvasContext} context where to draw
 * @param {double} coordinatesWidth needed for position function, look there for details
 * @param {int} startHeight needed for position function, look there for details
 * @param {boolean} isFullDraw full draw is for color and not full it only white elipse before full draw with opacity
 * @param {array of Exon} exons 
 * @param {int} domainHeight in pixel units
 * @param {double} domainY  in pixel units
 * @param {double} domainX  in pixel units
 * @param {double} domainWidth  in pixel units
 */
    drawExtend(context, coordinatesWidth, startHeight, isFullDraw, exons, domainHeight, domainY, domainX, domainWidth) {
        //position
        var pos = this.position(coordinatesWidth, startHeight);
        var domainWidth = pos.domainWidth;
        var domainX = pos.domainX;

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
        context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, domainWidth / 2, domainHeight / 2, 0, 0, 2 * Math.PI);
        // if (shapeID == 0 || true) {
        //     context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, domainWidth / 2, domainHeight / 2, 0, 0, 2 * Math.PI);
        // } else if (shapeID == 1) {
        //     context.moveTo(domainX, domainY);
        //     context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
        //     context.lineTo(domainX + domainWidth, domainY);
        // } else if (shapeID == 2) {
        //     context.moveTo(domainX, domainY);
        //     context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
        //     context.lineTo(domainX + domainWidth, domainY);
        // } else if (shapeID == 3) {
        //     context.moveTo(domainX + domainWidth / 2, domainY);
        //     context.lineTo(domainX + domainWidth, domainY + domainHeight / 2);
        //     context.lineTo(domainX + domainWidth / 2, domainY + domainHeight);
        //     context.lineTo(domainX, domainY + domainHeight / 2);
        // }
        context.closePath();

        //fill by overlap choice
        // if (false /*overlap*/ ) {
        //     context.globalAlpha = 0.3;
        //     context.fill();
        //     context.globalAlpha = 1;
        // } else {
        //     context.fill();
        // }

        //fill
        context.fill();

        //border
        context.strokeStyle = "grey";
        context.lineWidth = 1;
        context.stroke();

        //show text if needed in diagonal
        // if (false /*domainText*/ ) {
        //     context.save();
        //     context.translate(domainX + domainWidth / 2, domainY + domainHeight + 8);
        //     context.rotate(Math.PI / 16);
        //     var lineheight = 15;
        //     var lines = domainName.split('\n');
        //     context.fillStyle = "black"; //for text
        //     context.font = "20px Calibri"; //bold 

        //     //we must draw each line saperatly because canvas can't draw '\n'
        //     context.textAlign = "left";
        //     for (var i = 0; i < lines.length; i++) {
        //         context.fillText(lines[i], 0, 10 + (i * lineheight));
        //     }
        //     context.restore();
        // }


    }

    /**
     * tooltip info for fourth view (extended view)
     * @param {double} coordinatesWidth needed for tooltip, check there
     * @param {int} startHeight needed for tooltip, check there
     * @param {int} domainHeight in pixel units
     * @param {double} domainY in pixel units
     */
    proteinExtendTooltip(coordinatesWidth, startHeight, domainHeight, domainY) {
        var regulartooltip = this.tooltip(coordinatesWidth, startHeight);
        regulartooltip[1] = domainY;
        regulartooltip[3] = domainHeight;
        return [regulartooltip]; //saved in array because we take arrays of domains when it comes from domain group. here is a case where domain like a domainGroup of size 1
    }
    /**
     * when click on domain opening/closing fourth view in the tooltipManager
     * @param {tooltipManager} tooltipManager has values of each domain info and positions
     * @param {event} event click-event
     */
    static domainClick(tooltipManager, event) {
        var showTextValues = Transcript.showText(event, tooltipManager);
        if (showTextValues[0]) {
            if (showTextValues[2] == 'click' && tooltipManager[event.target.id + "object"] != undefined) { //if has a fourthview (means domains overlap enough)
                tooltipManager[event.target.id + "object"].proteinExtendView = !tooltipManager[event.target.id + "object"].proteinExtendView;
            }

        }
    }
/**
 * froup domains that are overlap in certain creteria of overlap
 * @param {array of Domain} domains 
 */
    static groupCloseDomains(domains) {
        //if nothing to group
        if (domains.length <= 1) {
            return domains;
        }

        //sorting
        function compare(a, b) {
            if (a.start < b.start) {
                return -1;
            }
            if (a.start > b.start) {
                return 1;
            }
            return b.end - a.end;
        }
        domains.sort(compare);

        //finding overlaps
        var finalDomains = [];
        var tempDomainArr = [domains[0]]; //used to make list of current candidates for grouping
        var groupStart = domains[0].start;
        var groupEnd = domains[0].end;
        for (var i = 1; i < domains.length; i++) {
            //if fully contains or significantly overlapping
            if ((domains[i].end <= groupEnd && groupStart <= domains[i].start) ||
                (domains[i].end >= groupEnd && groupStart >= domains[i].start) ||
                Domain.isDomainsInSignificantOverlap(groupStart, groupEnd, domains[i].start, domains[i].end)) {
                tempDomainArr.push(domains[i]);
                groupStart = Math.min(groupStart, domains[i].start);
                groupEnd = Math.max(groupEnd, domains[i].end);
            } else {
                //case not overlap
                if (tempDomainArr.length == 1) {
                    finalDomains.push(tempDomainArr[0]);
                } else if (tempDomainArr.length > 1) {
                    finalDomains.push(new DomainGroup(tempDomainArr));
                }
                tempDomainArr = [domains[i]];
                groupStart = domains[i].start;
                groupEnd = domains[i].end;

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
/**
 * returning if overlap is more than 50% of total area between two domains
 * @param {int} start1 start position of first domain
 * @param {int} end1 end position of first domain
 * @param {int} start2 start position of second domain
 * @param {int} end2 end position of second domain
 */
    static isDomainsInSignificantOverlap(start1, end1, start2, end2) {
        var common = Math.min(end1, end2) - Math.max(start1, start2);
        var all = Math.max(end1, end2) - Math.min(start1, start2);
        return (common / all) >= 0.5;

    }

}