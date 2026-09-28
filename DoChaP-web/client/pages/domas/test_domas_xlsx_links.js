/*
 * The workbook the Download button hands over carries the same DoChaP gene links
 * the results table on the page shows.
 *
 * Why this file exists: the server runs domas.py with -no_excel, so DOMAS's own
 * Excel writer - and its _link_gene_cells() - never runs in the web path. The
 * browser builds the workbook from the results CSV instead, and a CSV holds no
 * links, so for a while the download silently lost the links the page had just
 * displayed. Nothing else covers that path: DOMAS's tests/test_excel_links.py
 * exercises the Python writer, which this one never reaches.
 *
 * Run it with node, from anywhere:   node test_domas_xlsx_links.js
 * No test runner and no dependencies - the repo has neither, and adding one for
 * a single file is a worse trade than the twenty lines of harness below.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const CONTROLLER = path.join(__dirname, 'domasController.js');

// makeXlsx and its helpers are local to the controller's closure, which is the
// right place for them - they are not part of any public surface. To reach them
// the source is loaded with one line appended that hands them out, in memory;
// the file on disk is never touched.
function loadInternals(rewrite) {
    let source = fs.readFileSync(CONTROLLER, 'utf8');
    if (rewrite) source = rewrite(source);
    const at = source.lastIndexOf('\n});');
    if (at === -1) throw new Error('cannot find the end of the controller');
    source = source.slice(0, at) +
        '\n$scope.__internals = { makeXlsx: makeXlsx, geneHref: geneHref, ' +
        'concatParts: concatParts };\n' + source.slice(at);

    let controller = null;
    global.angular = { module: () => ({ controller: (name, fn) => { controller = fn; } }) };
    eval(source);                                     // eslint-disable-line no-eval
    if (!controller) throw new Error('the controller did not register');

    // .call with an instance, not a plain call: the controller opens with
    // `var self = this;` because Angular instantiates it, and this file is
    // strict mode, where a plain call would leave `this` undefined.
    // $window is stubbed rather than mocked - geneHref() builds the link from
    // its location, so these two values are what the expected URLs below assume.
    const $scope = {};
    controller.call({}, $scope,
                    { post: () => ({ then: () => {} }) },
                    { location: { origin: 'https://dochap.bgu.ac.il', pathname: '/' } },
                    {});
    return $scope.__internals;
}

// --- the smallest zip reader that can check this file's output ---------------
// Entries are written with method 0 (stored), so reading them back is a matter
// of walking the local headers. Deflate is handled anyway, so the reader does
// not quietly break if makeZip ever starts compressing.
function unzip(bytes) {
    const buf = Buffer.from(bytes);
    const files = {};
    let at = 0;
    while (at + 4 <= buf.length && buf.readUInt32LE(at) === 0x04034b50) {
        const method = buf.readUInt16LE(at + 8);
        const compressed = buf.readUInt32LE(at + 18);
        const nameLength = buf.readUInt16LE(at + 26);
        const extraLength = buf.readUInt16LE(at + 28);
        const name = buf.slice(at + 30, at + 30 + nameLength).toString('utf8');
        const start = at + 30 + nameLength + extraLength;
        const data = buf.slice(start, start + compressed);
        files[name] = method === 0 ? data.toString('utf8')
                                   : zlib.inflateRawSync(data).toString('utf8');
        at = start + compressed;
    }
    return files;
}

let failures = 0;
function check(what, condition) {
    if (condition) { console.log('  pass  ' + what); }
    else { failures++; console.log('  FAIL  ' + what); }
}

const { makeXlsx, concatParts } = loadInternals();

const CSV = [
    'event,alternative_transcripts_group,gene_symbol,species,event_effect_on_domain,' +
        'canonical_transcript_id,alternative_transcript_id,canonical_domain_length',
    'chr16:clu_15039,2/3,HERPUD1,human,shorter_domain,ENST00000254508.8,ENST00000379792.6,75',
    'chr2:clu_294,1/1,SRSF7,human,domain_loss,ENST00000313117.9,ENST00000425941.6,65',
    'chrX:clu_1,1/1,,human,no_gene_specified,,,'
].join('\n');

const parts = unzip(concatParts(makeXlsx(CSV, 'compared')));
const sheet = parts['xl/worksheets/sheet1.xml'];
const rels = parts['xl/worksheets/_rels/sheet1.xml.rels'] || '';

console.log('a linked workbook');
check('carries a rels part for the sheet', 'xl/worksheets/_rels/sheet1.xml.rels' in parts);
check('carries a styles part', 'xl/styles.xml' in parts);
check('declares the styles part in [Content_Types].xml',
      /PartName="\/xl\/styles\.xml"/.test(parts['[Content_Types].xml']));
check('relates the styles part to the workbook',
      /Target="styles\.xml"/.test(parts['xl/_rels/workbook.xml.rels']));
check('declares the r: namespace the hyperlink ids need',
      /<worksheet[^>]+xmlns:r=/.test(sheet));

// gene_symbol is the third column, so the links land on C2 and C3 - and NOT on
// C4, whose row names no gene, nor on C1, the header.
check('links the gene cell of each row that names a gene',
      /<hyperlink ref="C2" r:id="rId1"\/>/.test(sheet) &&
      /<hyperlink ref="C3" r:id="rId2"\/>/.test(sheet));
check('leaves a row naming no gene unlinked', !/ref="C4"/.test(sheet));
check('leaves the header unlinked', !/ref="C1"/.test(sheet));
check('places <hyperlinks> after </sheetData>',
      sheet.indexOf('<hyperlinks>') > sheet.indexOf('</sheetData>'));

check('resolves rId1 to that gene\'s DoChaP page, with both transcripts',
      rels.includes('Target="https://dochap.bgu.ac.il/#!/results/H_sapiens/HERPUD1/' +
                    'ENST00000254508.8%2CENST00000379792.6"'));
check('marks the targets external', (rels.match(/TargetMode="External"/g) || []).length === 2);
check('emits one relationship per link',
      (rels.match(/Type="[^"]*\/hyperlink"/g) || []).length === 2);

check('draws the linked cells in the hyperlink style',
      /<c r="C2" s="1"/.test(sheet) && /<c r="C3" s="1"/.test(sheet));
check('leaves every other cell in the default style', !/<c r="A2" s="1"/.test(sheet));
check('underlines the hyperlink font', /<font><u\/>/.test(parts['xl/styles.xml']));
check('states the hyperlink colour as an rgb, not a theme reference',
      /<color rgb="FF0563C1"\/>/.test(parts['xl/styles.xml']) &&
      !/theme="10"/.test(parts['xl/styles.xml']));
check('names the default cell style, so a reader does not substitute its own',
      /<cellStyle name="Normal"/.test(parts['xl/styles.xml']));

// The two typing rules the links must not disturb.
check('still writes a numeric column as a number', /<c r="H2"><v>75<\/v><\/c>/.test(sheet));
check('still writes alternative_transcripts_group as text (it reads "2/3")',
      /<c r="B2" t="inlineStr"><is><t xml:space="preserve">2\/3</.test(sheet));

console.log('\na workbook past Excel\'s link ceiling');
// Excel refuses to open a worksheet holding too many hyperlinks, so past the
// ceiling the workbook is written WITHOUT them rather than written broken - the
// same trade junction_analisys makes. Reaching the real 65,530 would mean
// building a sheet that large, so the constant is lowered in the loaded copy
// instead; that it is a single named constant is what makes this checkable.
const lowered = loadInternals(
    (src) => src.replace('var EXCEL_MAX_HYPERLINKS = 65530;',
                         'var EXCEL_MAX_HYPERLINKS = 2;'));
const many = ['gene_symbol,species']
    .concat(Array.from({ length: 5 }, (_, i) => 'G' + i + ',human')).join('\n');
const over = unzip(lowered.concatParts(lowered.makeXlsx(many, 'compared')));
const overSheet = over['xl/worksheets/sheet1.xml'];

check('writes no sheet rels part', !('xl/worksheets/_rels/sheet1.xml.rels' in over));
check('writes no <hyperlinks> block', !overSheet.includes('<hyperlinks>'));
check('leaves the gene cells in the default style', !/ s="1"/.test(overSheet));
check('still writes every row', (overSheet.match(/<row /g) || []).length === 6);
check('still writes the gene symbols themselves', overSheet.includes('G4'));

// ...and one row under the same lowered ceiling is still linked, so the check
// above is testing the limit rather than a link path that simply never runs.
const under = unzip(lowered.concatParts(
    lowered.makeXlsx(['gene_symbol,species', 'MBD2,human'].join('\n'), 'compared')));
check('a sheet under the ceiling is still linked',
      'xl/worksheets/_rels/sheet1.xml.rels' in under);

console.log('\n' + (failures ? failures + ' FAILED' : 'all checks passed'));
process.exit(failures ? 1 : 0);
