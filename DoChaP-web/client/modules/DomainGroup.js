class DomainGroup {
    /**
     * group domains into a domain-group
     * @param {array of Domain} domains 
     */
    constructor(domains) {
        this.domains = domains //arr of Domain objects
        // this.isExtend=isExtend;

        //init attributes
        this.start = domains[0].start;
        this.end = domains[0].end;

        //finding largest domain of them all and add to name
        this.name = this.getName();

        //choosing order for domains in the group
        this.orderDomains();

    }

    /**
     * drawing on canvas
     * @param {contextCanvas} context context to draw on
     * @param {double} coordinatesWidth the measure of scaling used
     * @param {int} startHeight size between the top of the canvas to the top of the domain
     * @param {boolean} isFullDraw full draw is regular draw 
     * and not full draw is just a white circle needed before drawing for opacity aesthetics
     * @param {array of Exon} exons 
     */
    draw(context, coordinatesWidth, startHeight, isFullDraw, exons) {
        //calculate positions
        var domainWidth = (this.end - this.start) * coordinatesWidth;
        var domainX = this.start * coordinatesWidth;
        var domainHeight = 45;
        var domainY = startHeight - domainHeight / 2;
        // var shapeID = 0; //currently its only circles 
        var overlap = false; //all point is that overlapped is inside
        var domainName = this.name.replace(/_/g, "\n").replace(/ /g, "\n");


        //choosing draw settings. if undefined it is background white so half transparent domain will look better 
        if (isFullDraw == false) {
            context.fillStyle = "white";
            var domainText = false;
        } else {
            var gradient = this.getGradientForDomain(context, domainX, domainX + domainWidth, startHeight, exons);
            context.fillStyle = gradient;
            var domainText = true;
        }

        //just in case
        context.closePath();

        //it is two circle on eachother to know there are overlapping domains
        context.beginPath();
        context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, domainWidth / 2, domainHeight / 2, 0, 0, 2 * Math.PI);
        context.closePath();

        //adding shadow
        context.save();
        context.shadowColor = "#898";
        context.shadowBlur = 6;
        context.shadowOffsetX = 2;
        context.shadowOffsetY = 2;

        //fill colors
        context.fill();

        //end shadow
        context.restore();

        //border
        context.strokeStyle = "grey";
        context.lineWidth = 2;
        context.stroke();

        //drawing inner eclipse
        context.beginPath();
        context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, Math.max(domainWidth / 2 - 10, 0.1), Math.max(domainHeight / 2 - 10, 0.1), 0, 0, 2 * Math.PI);
        context.closePath();

        //fill colors
        context.fill();

        //border
        context.strokeStyle = "grey";
        context.lineWidth = 2;
        context.stroke();

        //show text if needed in diagonal
        if (domainText) {
            //rotate
            context.save();
            context.translate(domainX + domainWidth / 2, domainY + domainHeight + 8);
            context.rotate(Math.PI / 16);
            //text style
            var lineheight = 15;
            var lines = domainName.split('\n');
            context.fillStyle = "black"; //for text
            context.font = "20px Calibri"; //bold 
            //adding shadow
            context.shadowColor = "#898";
            context.shadowBlur = 4;
            context.shadowOffsetX = 2;
            context.shadowOffsetY = 3;

            //we must draw each line saperatly because canvas can't draw '\n'
            context.textAlign = "left";
            for (var i = 0; i < lines.length; i++) {
                context.fillText(lines[i], 0, 10 + (i * lineheight));
            }

            //end shadow and rotate
            context.restore();
        }


    }
    /** 
     * drawing in the extended protein view (fourth view) which shows overlapping domains one below other so they are not overlapping
     * @param {contextCanvas} context context to draw on
     * @param {double} coordinatesWidth the measure of scaling used
     * @param {int} startHeight size between the top of the canvas to the top of the domaingroup
     * @param {boolean} isFullDraw full draw is regular draw
     * and not full draw is just a white circle needed before drawing for opacity aesthetics
     * @param {array of Exon} exons 
     */
    drawExtend(context, coordinatesWidth, startHeight, isFullDraw, exons, height) {
        //calculate positions
        var domainWidth = (this.end - this.start) * coordinatesWidth;
        var domainX = this.start * coordinatesWidth;
        var domainHeight = height - startHeight;
        var domainY = startHeight; //- domainHeight / 2
        // var shapeID = 0; //currently its only circles 
        var overlap = false; //all point is that overlapped is inside
        var domainName = this.name.replace(/_/g, "\n").replace(/ /g, "\n");

        //height for each domain in the group
        var oneDomainHeight = 25; //in pixel 

        //drwing each of the inner domains
        for (var i = 0; i < this.domains.length; i++) {
            this.domains[i].drawExtend(context, coordinatesWidth, startHeight, isFullDraw, exons, oneDomainHeight, domainY + oneDomainHeight * i, domainX, domainWidth);
        }
    }


    /**
     * calculations of gradient color
     * @param {canvasContext} context context to draw on
     * @param {int} start start position on axis of the protein
     * @param {int} end end position on axis of the protein
     * @param {int} height height of the domain to color
     * @param {array of Exon} exons has colors for each exons which will be used
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
            }
            //the starting color for the domain
            else if (exonStart <= this.start && this.start <= exonEnd) {
                gradient.addColorStop(0, exons[i].color);
                var position = Math.max(0, (exonEnd - this.start - whiteLineRadius) * normalizer);
                gradient.addColorStop(position, exons[i].color);
                //white line for splice junction
                gradient.addColorStop((exonEnd - this.start) * normalizer, "white");
            }
            //ending color for domain
            else if (exonStart <= this.end && this.end <= exonEnd) {
                var position = Math.min(1, (exonStart - this.start + whiteLineRadius) * normalizer);
                gradient.addColorStop(position, exons[i].color);
                gradient.addColorStop(1, exons[i].color);
            }
            //color for exon in the middle (not starting or finishing)
            else if (this.start <= exonStart && exonEnd <= this.end) {

                //white line for splice junction
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
     * creating tooltip info for this group of domains
     * @param {*} coordinatesWidth - needed for position calculations, check position for details
     * @param {*} startHeight  - needed for position calculations, check position for details
     */
    tooltip(coordinatesWidth, startHeight) {
        var domainWidth = (this.end - this.start) * coordinatesWidth;
        var domainHeight = 45;
        var domainX = this.start * coordinatesWidth;
        var domainY = startHeight - domainHeight / 2;
        var text = this.domains.length + " Domains. Click to expand";

        return [domainX, domainY, domainWidth, domainHeight, text, 'click'];
    }

    /**
     * tooltip info for fourth view (extended view)
     * @param {double} coordinatesWidth needed for tooltip, check there
     * @param {int} startHeight needed for tooltip, check there
     * @param {int} domainHeight in pixel units
     * @param {double} domainY in pixel units
     */
    proteinExtendTooltip(coordinatesWidth, startHeight, height) {
        // var domainWidth = (this.end - this.start) * coordinatesWidth;
        // var domainX = this.start * coordinatesWidth;
        var domainHeight = height - startHeight;
        var domainY = startHeight; //- domainHeight / 2
        // var shapeID = 0; //currently its only circles 
        // var overlap = false; //all point is that overlapped is inside
        // var domainName = this.name.replace(/_/g, "\n").replace(/ /g, "\n");
        var oneDomainHeight = 25; //in pixel

        var tooltips = [];
        for (var i = 0; i < this.domains.length; i++) {
            tooltips.push(this.domains[i].proteinExtendTooltip(coordinatesWidth, startHeight, oneDomainHeight, domainY + oneDomainHeight * i)[0]);
        }
        return tooltips;

    }


    /**
     * get name of largest domain that is not id
     */
    getName() {
        var domains = this.domains;
        var nameDict = {}
        for (var i = 0; i < domains.length; i++) {
            if (nameDict[domains[i].name] == undefined) {
                nameDict[domains[i].name] = 0;
            }
            nameDict[domains[i].name] = nameDict[domains[i].name] + 1;
        }

        //go through dictionary and if a name is majority we take it
        for (var key in nameDict) {
            if (nameDict.hasOwnProperty(key)) {
                if (nameDict[key] >= domains.length / 2) {
                    return key;
                }
            }
        }

        //taking the largest domain without name that is ID
        var largestLength = domains[0].end - domains[0].start;
        var largestLengthIndex = 0;
        for (var i = 0; i < domains.length; i++) {
            if (this.start > domains[i].start) {
                this.start = domains[i].start;
            }
            if (this.end < domains[i].end) {
                this.end = domains[i].end;
            }
            if (largestLength < domains[i].end - domains[i].start && Species.isNotID(domains[i].name)) {
                largestLength = domains[i].end - domains[i].start;
                largestLengthIndex = i;
            }
        }

        return domains[largestLengthIndex].name;
    }


    /**
     * orders domains so when needed they will be in wanted order
     */
    orderDomains() {
        function compare(a, b) {
            if (a.start < b.start) {
                return -1;
            }
            if (a.start > b.start) {
                return 1;
            }
            return b.end - a.end;
        }
        this.domains.sort(compare);
    }
}