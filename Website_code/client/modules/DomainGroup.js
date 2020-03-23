class DomainGroup {
    constructor(domains,isExtend) {
        this.domains=domains //arr of Domain objects
        this.isExtend=isExtend;

        //init attributes
        this.start=domains[0].start;
        this.end=domains[0].end;
        var largestLength=domains[0].end-domains[0].start;
        var largestLengthIndex=0;
        for(var i=0; i<domains.length;i++){
            if(this.start>domains[i].start){
                this.start=domains[i].start;
            }
            if(this.end<domains[i].end){
                this.end=domains[i].end;
            }
            if(largestLength < domains[i].end-domains[i].start ){
                largestLength=domains[i].end-domains[i].start;
                largestLengthIndex=i;
            }
        }
       
        //init name by largest domain
        this.name=domains[largestLengthIndex].name;
    }
  
    draw(context, coordinatesWidth, startHeight, isFullDraw, exons) {
        var domainWidth = (this.end - this.start) * coordinatesWidth;
        var domainX = this.start * coordinatesWidth;
        var domainHeight = 45;
        var domainY = startHeight - domainHeight / 2;
        var shapeID = 0; //currently its only circles 
        var overlap = false; //all point is that overlapped is inside
        var domainName = this.name.replace(/_/g, "\n").replace(/ /g, "\n");


        //choosing draw settings. if undefined it is background white so half transparent domain will look better 
        if (isFullDraw == false) {
            context.fillStyle = "white";
            var domainText = false;
        } else {
            var gradient = this.getGradientForDomain( context,domainX, domainX + domainWidth, startHeight, exons);
            context.fillStyle = gradient;
            var domainText = true;
        }

        //only circles- notice it is two circle on eachother
        context.beginPath();
        context.ellipse(domainX + domainWidth / 2, domainY + domainHeight / 2, domainWidth / 2, domainHeight / 2, 0, 0, 2 * Math.PI);
        context.closePath();
        context.fill();
        
        //border
        context.strokeStyle = "grey";
        context.lineWidth = 1;
        context.stroke();

        context.beginPath();
        context.ellipse(domainX + domainWidth / 2 , domainY + domainHeight / 2 , Math.max(domainWidth / 2 -10,0.1),  Math.max( domainHeight / 2 -10,0.1), 0, 0, 2 * Math.PI);
        context.closePath();
        context.fill();
        
        //border
        context.strokeStyle = "grey";
        context.lineWidth = 1;
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

            //we must draw each line saperatly because canvas can't draw '\n'
            context.textAlign = "left";
            for (var i = 0; i < lines.length; i++) {
                context.fillText(lines[i], 0, 10 + (i * lineheight));
            }
            context.restore();
        }


    }

    drawExtend(context, coordinatesWidth, startHeight, isFullDraw, exons) {
        var domainWidth = (this.end - this.start) * coordinatesWidth;
        var domainX = this.start * coordinatesWidth;
        var domainHeight = 45;
        var domainY = startHeight - domainHeight / 2;
        var shapeID = 0; //currently its only circles 
        var overlap = false; //all point is that overlapped is inside
        var domainName = this.name.replace(/_/g, "\n").replace(/ /g, "\n");

        var oneDomainHeight=domainHeight/this.domains.length;
        for(var i=0; i<this.domains.length;i++){
            this.domains[i].drawExtend(context,coordinatesWidth,startHeight,isFullDraw,exons,oneDomainHeight,domainY+oneDomainHeight*i,domainX,domainWidth);
        }
    }


    //calculations of gradient color
    getGradientForDomain(context, start, end, height, exons) { //exons are absolute position for this to work
        var gradient = context.createLinearGradient(start, height, end, height); //contextP only for domains now
        var whiteLineRadius = 10;
        var normalizer= 1 /(this.end - this.start);
        for (var i = 0; i < exons.length; i++) {
            var exonStart=exons[i].transcriptViewStart;
            var exonEnd=exons[i].transcriptViewEnd;
            if (exonStart <= this.start && this.start <= exonEnd && exonStart <= this.end && this.end <= exonEnd) {
                //no junctions so only one color
                return exons[i].color;
            }
            else if (exonStart <= this.start && this.start <= exonEnd) {
                //the starting color for the domain
                gradient.addColorStop(0, exons[i].color);
                var position = Math.max(0, (exonEnd - this.start - whiteLineRadius) * normalizer);
                gradient.addColorStop(position, exons[i].color);
                //white line (if wanted)
                gradient.addColorStop((exonEnd - this.start) *normalizer, "white");
            }
            else if (exonStart <= this.end && this.end <= exonEnd) {
                //ending color for domain
                var position = Math.min(1, (exonStart - this.start + whiteLineRadius)*normalizer);
                gradient.addColorStop(position, exons[i].color);
                gradient.addColorStop(1, exons[i].color);
            }
            else if (this.start <= exonStart && exonEnd <= this.end) {
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

    tooltip(coordinatesWidth,startHeight) {
        var domainWidth = (this.end - this.start) * coordinatesWidth;
        var domainHeight = 45;
        var domainX = this.start * coordinatesWidth;
        var domainY = startHeight - domainHeight / 2;
        
        //for tooltip text
        var name=this.name;
        var start=this.AAstart;
        var end=this.AAend;
        var length=end-start;
        var text= ""+this.domains.length+" DOMAINS:";

        for(var i=0; i<this.domains.length;i++){
            text=text+"<br>"+this.domains[i].tooltip(coordinatesWidth,startHeight)[4];
        }
        var text=this.domains.length+" Domains";
        return [domainX, domainY, domainWidth, domainHeight, text, undefined];
    }

    proteinExtendTooltip(coordinatesWidth,startHeight){
        var domainWidth = (this.end - this.start) * coordinatesWidth;
        var domainX = this.start * coordinatesWidth;
        var domainHeight = 45;
        var domainY = startHeight - domainHeight / 2;
        var shapeID = 0; //currently its only circles 
        var overlap = false; //all point is that overlapped is inside
        var domainName = this.name.replace(/_/g, "\n").replace(/ /g, "\n");
        var oneDomainHeight=domainHeight/this.domains.length;

        var tooltips=[];
        for(var i=0; i<this.domains.length;i++){
            tooltips.push(this.domains[i].proteinExtendTooltip(coordinatesWidth,startHeight,oneDomainHeight,domainY+oneDomainHeight*i,domainX,domainWidth)[0]);
        }
        return tooltips;
        
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
    
}