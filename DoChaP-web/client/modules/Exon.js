class Exon {
	/**
	 *
	 * @param {array of transcriptExon table rows} dbExon
	 * @param {dictionary of colors} colors
	 * @param {int} cdsStart cds start in nuc units
	 * @param {int} cdsEnd cds start in nuc units
	 * @param {int} numOfExonInTranscript number of exons in all transcript
	 * @param {int} startCoordinate where genomic zoom in start is
	 * @param {int} proteinStart where zoom in protein start is
	 * @param {int} cutLength if we need to cut then non-zerp length
	 */
	constructor(
		dbExon,
		colors,
		cdsStart,
		cdsEnd,
		numOfExonInTranscript,
		startCoordinate = 0,
		proteinStart = 0,
		cutLength = 0
	) {
		//init attributes
		this.cutLength = cutLength;
		this.genomicViewStart = dbExon.genomic_start_tx - startCoordinate - 1; //-1  because it is zero based
		this.genomicViewEnd = dbExon.genomic_end_tx - startCoordinate;
		this.transcriptViewStart = dbExon.abs_start_CDS - proteinStart;
		this.transcriptViewEnd = dbExon.abs_end_CDS - proteinStart;
		this.id = dbExon.abs_end;
		this.orderInTranscript = dbExon.order_in_transcript;
		this.numOfExonInTranscript = numOfExonInTranscript;
		this.length = dbExon.abs_end_CDS - dbExon.abs_start_CDS + 1; //in nuc
		this.genomic_start_tx = dbExon.genomic_start_tx;
		this.genomic_end_tx = dbExon.genomic_end_tx;
		this.abs_start_CDS = dbExon.abs_start_CDS;
		this.abs_end_CDS = dbExon.abs_end_CDS;

		//utr attributes
		this.isUTRStart = undefined;
		this.isUTREnd = undefined;
		this.isUTRAll = false;

		//finding utr for later drawings
		if (dbExon.abs_start_CDS == 0) {
			//that is the representation is the database
			this.isUTRAll = true;
		} else {
			if (
				dbExon.genomic_start_tx <= cdsStart &&
				cdsStart <= dbExon.genomic_end_tx
			) {
				//cds_start in mid exon
				this.isUTRStart = cdsStart - dbExon.genomic_start_tx;
			}
			if (
				dbExon.genomic_start_tx <= cdsEnd &&
				cdsEnd <= dbExon.genomic_end_tx
			) {
				//cds_end in mid exon
				this.isUTREnd = dbExon.genomic_end_tx - cdsEnd;
			}
		}

		let colorLimits = Exon.getExonLimitsForColoring(dbExon.genomic_start_tx, dbExon.genomic_end_tx,
			dbExon.abs_start_CDS, cdsStart, cdsEnd);
		this.color =
			colors[colorLimits.start]
			[colorLimits.end]
			.color;
	}

	/**
	 *draw rectangle, border and text or polygon if not all exon is in cds. note that utrStart and utrEnd are bases in the beginning or end that are out of the cds. if all is out utrAll is true
	 * @param {canvasContext} context context to draw on
	 * @param {int} startHeight size between the top of the canvas to the top of the exon
	 * @param {double} coordinatesWidth the measure of scaling used
	 * @param {int} beginningEmpty the space before the first exon start
	 * @param {int} endEmpty the space after the last exon end
	 * @param {int} canvasWidth
	 * @param {boolean} isStrandNegative if the strand is '-'
	 * @param {int} spaceAfterCut if cut exists the length of the 'cuting' drawing
	 */
	drawExonInGenomicView(
		context,
		position
	) {
		const exonWidth = position.exonWidth;
		const exonHeight = position.exonHeight;
		const exonX = position.exonX;
		const exonY = position.exonY;
		const coordinatesWidth = position.coordinatesWidth;
		const isStrandNegative = position.isStrandNegative;

		var utrLeft = this.isUTRStart;
		var utrRight = this.isUTREnd;
		const utrAll = this.isUTRAll;

		if (isStrandNegative) {
			var utrLeft = this.isUTREnd;
			var utrRight = this.isUTRStart;
		}

		context.beginPath();
		if (utrLeft == undefined && utrRight == undefined && !utrAll) {
			context.rect(exonX, exonY, exonWidth, exonHeight); //no utr
		} else if (utrAll) {
			context.rect(exonX, exonY + exonHeight / 4, exonWidth, exonHeight / 2); //all utr
		} else if (utrLeft != undefined && utrRight == undefined) {
			//utr in the left only
			context.moveTo(exonX, exonY + exonHeight / 4);
			context.lineTo(exonX, exonY + (3 * exonHeight) / 4);
			context.lineTo(
				exonX + utrLeft * coordinatesWidth,
				exonY + (3 * exonHeight) / 4
			);
			context.lineTo(exonX + utrLeft * coordinatesWidth, exonY + exonHeight);
			context.lineTo(exonX + exonWidth, exonY + exonHeight);
			context.lineTo(exonX + exonWidth, exonY);
			context.lineTo(exonX + utrLeft * coordinatesWidth, exonY);
			context.lineTo(
				exonX + utrLeft * coordinatesWidth,
				exonY + exonHeight / 4
			);
		} else if (utrLeft == undefined && utrRight != undefined) {
			//utr in the right only
			context.moveTo(exonX, exonY);
			context.lineTo(exonX, exonY + exonHeight);
			context.lineTo(
				exonX + exonWidth - utrRight * coordinatesWidth,
				exonY + exonHeight
			);
			context.lineTo(
				exonX + exonWidth - utrRight * coordinatesWidth,
				exonY + (3 * exonHeight) / 4
			);
			context.lineTo(exonX + exonWidth, exonY + (3 * exonHeight) / 4);
			context.lineTo(exonX + exonWidth, exonY + exonHeight / 4);
			context.lineTo(
				exonX + exonWidth - utrRight * coordinatesWidth,
				exonY + exonHeight / 4
			);
			context.lineTo(exonX + exonWidth - utrRight * coordinatesWidth, exonY);
		} else if (utrLeft != undefined && utrRight != undefined) {
			//utr in both sizes
			context.moveTo(exonX, exonY + exonHeight / 4);
			context.lineTo(exonX, exonY + (3 * exonHeight) / 4);
			context.lineTo(
				exonX + utrLeft * coordinatesWidth,
				exonY + (3 * exonHeight) / 4
			);
			context.lineTo(exonX + utrLeft * coordinatesWidth, exonY + exonHeight);
			context.lineTo(
				exonX + exonWidth - utrRight * coordinatesWidth,
				exonY + exonHeight
			);
			context.lineTo(
				exonX + exonWidth - utrRight * coordinatesWidth,
				exonY + (3 * exonHeight) / 4
			);
			context.lineTo(exonX + exonWidth, exonY + (3 * exonHeight) / 4);
			context.lineTo(exonX + exonWidth, exonY + exonHeight / 4);
			context.lineTo(
				exonX + exonWidth - utrRight * coordinatesWidth,
				exonY + exonHeight / 4
			);
			context.lineTo(exonX + exonWidth - utrRight * coordinatesWidth, exonY);
			context.lineTo(exonX + utrLeft * coordinatesWidth, exonY);
			context.lineTo(
				exonX + utrLeft * coordinatesWidth,
				exonY + exonHeight / 4
			);
		}
		context.closePath();

		//adding shadows and coloring inside
		context.save();
		context.translate(0, 0);
		context.shadowColor = "#898";
		context.shadowBlur = 4;
		context.shadowOffsetX = 2;
		context.shadowOffsetY = 3;
		context.fillStyle = this.color;
		context.fill();
		context.restore();

		//border
		context.strokeStyle = "grey";
		context.stroke();
	}

	/**
	 * draw rectangle, border and text
	 * @param {canvasContext} context context to draw on
	 * @param {double} coordinatesWidth the measure of scaling used
	 * @param {int} startHeight size between the top of the canvas to the top of the exon
	 */
	drawExonInTranscriptView(context, coordinatesWidth, startHeight) {
		//if not in cds so it does not show in *transcript view*
		if (this.transcriptViewStart == 0) {
			return;
		}

		//position
		var position = this.transcriptViewPosition(coordinatesWidth, startHeight);
		var exonWidth = position.exonWidth;
		var exonHeight = position.exonHeight;
		var exonX = position.exonX;
		var exonY = position.exonY;

		//background color
		context.fillStyle = this.color;
		context.fillRect(exonX, exonY, exonWidth, exonHeight);

		//border
		context.strokeStyle = "grey";
		context.strokeRect(exonX, exonY, exonWidth, exonHeight);
	}

	/**
	 * tooltip for exon in genomic view
	 * @param {int} startHeight startHeight size between the top of the canvas to the top of the exon
	 * @param {double} coordinatesWidth the measure of scaling used
	 * @param {int} beginningEmpty the space before the first exon start
	 * @param {int} endEmpty the space after the last exon end
	 * @param {int} canvasWidth
	 * @param {boolean} isStrandNegative  if the strand is '-'
	 * @param {int} spaceAfterCut if cut exists the length of the 'cuting' drawing
	 */

	genomicTooltip(
		position
	) {

		const exonWidth = position.exonWidth;
		const exonHeight = position.exonHeight;
		const exonX = position.exonX;
		const exonY = position.exonY;
		const text =
			"Exon: " +
			this.orderInTranscript +
			"/" +
			this.numOfExonInTranscript +
			"<br>" +
			numberToTextWithCommas(this.genomic_start_tx) +
			" - " +
			numberToTextWithCommas(this.genomic_end_tx);
		return [exonX, exonY, exonWidth, exonHeight, text, 'clickable', this];
	}

	/**
	 * tootip for exon in the transcript view
	 * @param {double} coordinatesWidth the measure of scaling used
	 * @param {int} startHeight startHeight size between the top of the canvas to the top of the exon
	 */
	transcriptTooltip(coordinatesWidth, startHeight) {
		const position = this.transcriptViewPosition(coordinatesWidth, startHeight);
		const exonWidth = position.exonWidth;
		const exonHeight = position.exonHeight;
		const exonX = position.exonX;
		const exonY = position.exonY;
		var text =
			"Exon: " +
			this.orderInTranscript +
			"/" +
			this.numOfExonInTranscript +
			"<br>Length: " +
			this.length +
			"bp";
		return [exonX, exonY, exonWidth, exonHeight, text, undefined];
	}

	/**
	 * finding the position for the exon to be drawn and have tooltip
	 * @param {double} coordinatesWidth the measure of scaling used
	 * @param {int} startHeight startHeight size between the top of the canvas to the top of the exon
	 */
	transcriptViewPosition(coordinatesWidth, startHeight) {
		var pos = new Object();
		pos.exonWidth =
			(this.transcriptViewEnd - this.transcriptViewStart + 1) *
			coordinatesWidth;
		pos.exonHeight = 25;
		pos.exonX = this.transcriptViewStart * coordinatesWidth;
		pos.exonY = startHeight - pos.exonHeight / 2;
		return pos;
	}

	/**
	 * position for exon to be drawn in genomic view
	 * @param {double} coordinatesWidth the measure of scaling used
	 * @param {int} startHeight size between the top of the canvas to the top of the exon
	 * @param {int} spaceAfterCut if cut exists the length of the 'cuting' drawing
	 * @param {int} beginningEmpty the space before the first exon start
	 * @param {int} canvasWidth
	 * @param {int} endEmpty the space after the last exon end
	 * @param {boolean} isStrandNegative  if the strand is '-'
	 *
	 */

	genomicViewPosition(
		coordinatesWidth,
		startHeight,
		spaceAfterCut,
		beginningEmpty,
		canvasWidth,
		endEmpty,
		isStrandNegative
	) {
		var pos = new Object();
		pos.coordinatesWidth = coordinatesWidth;
		pos.isStrandNegative = isStrandNegative;
		pos.spaceAfterCut = this.cutLength > 0 ? spaceAfterCut : 0;
		pos.exonWidth = Math.max(
			3,
			(this.genomicViewEnd - this.genomicViewStart + 1) * coordinatesWidth
		);
		pos.exonHeight = 70;
		pos.exonX =
			(this.genomicViewStart - this.cutLength) * coordinatesWidth +
			beginningEmpty +
			pos.spaceAfterCut;
		pos.exonY = startHeight - pos.exonHeight / 2;

		if (isStrandNegative) {
			pos.exonX =
				canvasWidth -
				(this.genomicViewStart - this.cutLength) * coordinatesWidth -
				endEmpty -
				pos.exonWidth -
				pos.spaceAfterCut;
		}

		return pos;
	}

	static getExonLimitsForColoring(tx_start, tx_end, allUtrFlag, cdsStart, cdsEnd) {
		var limits ={
				start: tx_start,
				end: tx_end
			};
		if (allUtrFlag == 0) {
			return limits;
		}
		if (
			tx_start <= cdsStart &&
			cdsStart <= tx_end
		) {
			limits.start = cdsStart;
		}
		if (
			tx_start <= cdsEnd &&
			cdsEnd <= tx_end
		) {
			limits.end = cdsEnd;
		}
		return limits;
	}
}