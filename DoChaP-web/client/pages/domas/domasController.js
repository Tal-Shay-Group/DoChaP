/**
 * DOMAS page controller.
 *
 * Reads the user-selected input file(s), base64-encodes them in the browser,
 * POSTs them to the server (which runs domas.py on the first 100 events),
 * then renders the returned results CSV as a table and offers it for download.
 *
 * Both runs also show the run summary the server returns beside the CSV.
 *
 * Also drives a self-contained "Try it with sample data" panel: its own
 * format selector and its own output display, entirely independent of the
 * manual-upload state above. One click (runExample) fetches a bundled example
 * dataset, POSTs it through the exact same /domas/process endpoint a real
 * upload uses, and renders the results - no server-side change needed for
 * this. The example files are plain static assets under
 * client/resources/domas_examples/, offered for download as a per-format zip
 * so they can be looked at, or fed back through the upload form, without
 * being dumped into the page.
 */
angular.module("DoChaP").controller('domasController', function ($scope, $http, $window, webService) {
    var self = this;

    // dropdown options; leafcutter is the default
    $scope.formats = [
        { value: 'leafcutter', label: 'LeafCutter' },
        { value: 'rmats', label: 'rMATS' },
        { value: 'majiq', label: 'MAJIQ' },
        { value: 'ioe', label: 'SUPPA (ioe)' }
    ];
    $scope.format = 'leafcutter';

    // Species the input was produced from. None of the supported files carry a
    // species field, so it always has to be stated.
    $scope.species = [
        { value: 'human', label: 'Human' },
        { value: 'mouse', label: 'Mouse' },
        { value: 'rat', label: 'Rat' }
    ];
    $scope.specie = 'human';

    $scope.loading = false;
    $scope.alert = '';
    $scope.columns = [];
    $scope.rows = [];
    $scope.totalRows = 0;
    $scope.clusterCount = 0;
    $scope.truncated = false;
    $scope.summaryText = '';          // the run summary, '' when there is none
    $scope.nonComparedText = '';      // the rows that reached no comparison
    $scope.showSummary = false;

    var csvText = '';                 // full CSV, kept for download
    var MAX_DISPLAY_ROWS = 500;       // cap table rows for responsiveness

    // columns whose values are always short - render them narrow
    var NARROW_COLUMNS = {
        canonical_domain_length: true, alternative_domain_length: true,
        canonical_domains_number: true, alternative_domains_number: true,
        is_longest_cds: true, is_most_like_canonical: true
    };
    $scope.isNarrow = function (col) { return NARROW_COLUMNS[col] === true; };

    // ---- gene_symbol -> the DoChaP page for that gene ---------------------
    // The /results/:specie/:query route filters Genes.specie on the database
    // spelling of the species (see querySearch.js), while the DOMAS CSV carries
    // the common name. Anything not in this map falls back to 'all', which the
    // server reads as "do not filter by species".
    var DB_SPECIE = { human: 'H_sapiens', mouse: 'M_musculus', rat: 'R_norvegicus' };

    // Absolute, because the link is opened in a new tab.
    function geneHref(gene, specie) {
        gene = (gene || '').trim();
        if (!gene) return null;
        return $window.location.origin + $window.location.pathname + '#!/results/' +
               (DB_SPECIE[(specie || '').trim().toLowerCase()] || 'all') + '/' +
               encodeURIComponent(gene);
    }

    function utf8ToBase64(str) {
        return btoa(unescape(encodeURIComponent(str)));
    }

    // minimal RFC-4180-ish CSV parser (handles quoted fields with commas/quotes/newlines)
    function parseCsv(text) {
        var rows = [], row = [], field = '', inQuotes = false, i, c;
        for (i = 0; i < text.length; i++) {
            c = text[i];
            if (inQuotes) {
                if (c === '"') {
                    if (text[i + 1] === '"') { field += '"'; i++; }
                    else inQuotes = false;
                } else field += c;
            } else if (c === '"') {
                inQuotes = true;
            } else if (c === ',') {
                row.push(field); field = '';
            } else if (c === '\n') {
                row.push(field); rows.push(row); row = []; field = '';
            } else if (c === '\r') {
                // ignore; handled by \n
            } else field += c;
        }
        // last field/row (if file doesn't end with newline)
        if (field.length > 0 || row.length > 0) { row.push(field); rows.push(row); }
        return rows;
    }

    // Parses a results CSV into {columns, rows, totalRows, truncated,
    // clusterCount}, or null if it has no data rows. Shared by the manual
    // upload flow and the example flow, each of which renders into its own
    // set of $scope variables.
    function summarizeCsv(csv) {
        var parsed = parseCsv(csv || '').filter(function (r) { return r.length > 1 || (r.length === 1 && r[0] !== ''); });
        if (parsed.length === 0) return null;
        var columns = parsed[0];
        var body = parsed.slice(1);
        var rows = body.slice(0, MAX_DISPLAY_ROWS);

        // Resolved once per row here rather than from the template, which would
        // re-evaluate it for every cell on every digest.
        var gIdx = columns.indexOf('gene_symbol');
        // domas.py writes this column as 'species'; older results say 'specie'.
        var sIdx = columns.indexOf('species');
        if (sIdx === -1) sIdx = columns.indexOf('specie');
        if (gIdx !== -1) {
            rows.forEach(function (r) {
                r.geneHref = geneHref(r[gIdx], sIdx === -1 ? '' : r[sIdx]);
            });
        }

        // count distinct clusters (the 'event' column, if present - it holds the
        // cluster id; 'cluster' is the name results produced before the rename)
        var cidx = columns.indexOf('event');
        if (cidx === -1) cidx = columns.indexOf('cluster');
        if (cidx === -1) cidx = columns.indexOf('cluster_name');
        var clusterCount;
        if (cidx !== -1) {
            var seen = {};
            body.forEach(function (r) { seen[r[cidx]] = true; });
            clusterCount = Object.keys(seen).length;
        } else {
            clusterCount = '?';
        }

        return { columns: columns, rows: rows, totalRows: body.length,
                 truncated: body.length > MAX_DISPLAY_ROWS, clusterCount: clusterCount };
    }

    // ------------------------------------------------------------------
    // Manual upload flow
    // ------------------------------------------------------------------

    // read one File as { name, role, content(base64) }
    function readFile(file, role) {
        return new Promise(function (resolve, reject) {
            var reader = new FileReader();
            reader.onload = function () {
                // reader.result is "data:<mime>;base64,<data>"
                var comma = reader.result.indexOf(',');
                resolve({ name: file.name, role: role, content: reader.result.substring(comma + 1) });
            };
            reader.onerror = function () { reject(new Error("Could not read " + file.name)); };
            reader.readAsDataURL(file);
        });
    }

    // collect the File objects for the current format, with validation
    function gatherFiles() {
        var el, i;
        if ($scope.format === 'leafcutter') {
            var sig = document.getElementById('lc_sig_file').files[0];
            var eff = document.getElementById('lc_effect_file').files[0];
            if (!sig || !eff) throw new Error("Please select both the cluster-significance and effect-sizes files.");
            return [readFile(sig, 'lc_sig'), readFile(eff, 'lc_effect')];
        }
        if ($scope.format === 'rmats') {
            el = document.getElementById('rmats_files');
            var reads = [];
            for (i = 0; i < el.files.length; i++) {
                // only upload the MATS.JC.txt files (skip any .gtf etc. in the folder)
                if (/MATS\.JC\.txt$/i.test(el.files[i].name)) {
                    reads.push(readFile(el.files[i], 'input'));
                }
            }
            if (reads.length === 0) throw new Error("Please select the rMATS *.MATS.JC.txt files.");
            return reads;
        }
        // majiq / ioe: single file
        el = document.getElementById('single_file');
        var f = el.files[0];
        if (!f) throw new Error("Please select an input file.");
        return [readFile(f, 'input')];
    }

    self.process = function () {
        $scope.alert = '';
        $scope.columns = [];
        $scope.rows = [];
        var reads;
        try {
            reads = gatherFiles();
        } catch (e) {
            $scope.alert = e.message;
            return;
        }

        $scope.loading = true;
        Promise.all(reads).then(function (files) {
            return webService.runDomas({
                format: $scope.format,
                specie: $scope.specie,
                files: files
            });
        }).then(function (response) {
            $scope.loading = false;
            csvText = response.data.csv || '';
            $scope.summaryText = response.data.summary || '';
            $scope.nonComparedText = response.data.nonCompared || '';
            $scope.showSummary = false;
            var summary = summarizeCsv(csvText);
            if (!summary) {
                $scope.alert = "DOMAS produced no results for this input.";
            } else {
                $scope.columns = summary.columns;
                $scope.rows = summary.rows;
                $scope.totalRows = summary.totalRows;
                $scope.truncated = summary.truncated;
                $scope.clusterCount = summary.clusterCount;
            }
            $scope.$applyAsync();
        }).catch(function (err) {
            $scope.loading = false;
            var msg = "Sorry, something went wrong.";
            if (err && err.data && err.data.error) msg = err.data.error;
            else if (err && err.message) msg = err.message;
            $scope.alert = msg;
            $scope.$applyAsync();
        });
    };

    // ---- handing the run's three files over as one download ---------------
    // A run produces the compared rows, the rows that never reached a
    // comparison, and the summary. They are built in memory and never exist as
    // URLs of their own, so the archive is assembled here.
    //
    // Written out by hand rather than with a zip library: the alternative is
    // another vendored dependency (see downloadVendorLibs.bat) for three small
    // text files. Entries are stored uncompressed - the format's method 0,
    // which every unzip tool reads - so the only real work is the CRC.

    var CRC_TABLE = (function () {
        var table = new Uint32Array(256), c, n, k;
        for (n = 0; n < 256; n++) {
            c = n;
            for (k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
            table[n] = c >>> 0;
        }
        return table;
    })();

    function crc32(bytes) {
        var c = 0xFFFFFFFF;
        for (var i = 0; i < bytes.length; i++) {
            c = CRC_TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
        }
        return (c ^ 0xFFFFFFFF) >>> 0;
    }

    // entries: [{name, text}] -> the parts of a .zip, in order.
    function makeZip(entries) {
        var encoder = new TextEncoder();      // the flag bit below says UTF-8
        var parts = [], central = [], offset = 0;

        function u16(v) { return [v & 0xFF, (v >>> 8) & 0xFF]; }
        function u32(v) { return [v & 0xFF, (v >>> 8) & 0xFF, (v >>> 16) & 0xFF, (v >>> 24) & 0xFF]; }

        entries.forEach(function (entry) {
            var name = encoder.encode(entry.name);
            var data = encoder.encode(entry.text);
            var sum = crc32(data);
            // local file header: version 10, UTF-8 flag, method 0 (stored),
            // no modification time, then the sizes - equal, being uncompressed.
            var header = [].concat(
                u32(0x04034b50), u16(10), u16(0x0800), u16(0), u16(0), u16(0),
                u32(sum), u32(data.length), u32(data.length),
                u16(name.length), u16(0));
            parts.push(new Uint8Array(header), name, data);
            central.push({ name: name, crc: sum, size: data.length, offset: offset });
            offset += header.length + name.length + data.length;
        });

        var directory = [];
        central.forEach(function (e) {
            directory = directory.concat(
                u32(0x02014b50), u16(20), u16(10), u16(0x0800), u16(0), u16(0), u16(0),
                u32(e.crc), u32(e.size), u32(e.size),
                u16(e.name.length), u16(0), u16(0), u16(0), u16(0), u32(0),
                u32(e.offset));
            directory = directory.concat(Array.from(e.name));
        });
        var end = [].concat(
            u32(0x06054b50), u16(0), u16(0), u16(central.length), u16(central.length),
            u32(directory.length), u32(offset), u16(0));

        parts.push(new Uint8Array(directory), new Uint8Array(end));
        return parts;
    }

    function downloadBlob(blob, filename) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // The run's files, skipping any the server did not send.
    function resultEntries(csv, nonCompared, summary) {
        var entries = [{ name: 'compared.csv', text: csv }];
        if (nonCompared) entries.push({ name: 'non_compared.csv', text: nonCompared });
        if (summary) entries.push({ name: 'run_summary.txt', text: summary });
        return entries;
    }

    function downloadResults(csv, nonCompared, summary, filename) {
        var entries = resultEntries(csv, nonCompared, summary);
        if (entries.length === 1) {          // nothing to bundle with it
            downloadBlob(new Blob([csv], { type: 'text/csv' }),
                         filename.replace(/\.zip$/, '.csv'));
            return;
        }
        downloadBlob(new Blob(makeZip(entries), { type: 'application/zip' }), filename);
    }

    self.downloadResults = function () {
        downloadResults(csvText, $scope.nonComparedText, $scope.summaryText,
                        'domas_results.zip');
    };

    // ------------------------------------------------------------------
    // "Try it with sample data" - self-contained, independent of the
    // manual-upload state above.
    // ------------------------------------------------------------------

    // Each entry mirrors what gatherFiles() would produce from a real upload:
    // a role the server expects, and the exact filename the server-side
    // reader looks for (matters for rmats, which matches on filename). All
    // three are real human data (ENSG* gene ids).
    var EXAMPLES = {
        leafcutter: [
            { role: 'lc_sig', filename: 'leafcutter_ds_cluster_significance.txt',
              url: 'resources/domas_examples/leafcutter/leafcutter_ds_cluster_significance.example.txt' },
            { role: 'lc_effect', filename: 'leafcutter_ds_effect_sizes.txt',
              url: 'resources/domas_examples/leafcutter/leafcutter_ds_effect_sizes.example.txt' }
        ],
        rmats: [
            { role: 'input', filename: 'SE.MATS.JC.txt',
              url: 'resources/domas_examples/rmats/SE.MATS.JC.txt' }
        ],
        majiq: [
            { role: 'input', filename: 'NveB_Mono_voila.txt',
              url: 'resources/domas_examples/majiq/NveB_Mono_voila.example.txt' }
        ]
    };

    // The same files, zipped, for downloading rather than running - built here
    // from the very files runExample() posts, so the archive cannot drift from
    // what the example actually runs on. Inside it they carry the names DOMAS
    // expects, so an unzipped copy goes straight back through the upload form
    // above. Committing prebuilt archives instead would mean binaries in the
    // repository that have to be rebuilt whenever a sample file changes.
    self.downloadExampleInput = function () {
        var specs = EXAMPLES[$scope.exampleFormat];
        if (!specs) return;
        var format = $scope.exampleFormat;
        $scope.exampleAlert = '';
        Promise.all(specs.map(function (spec) {
            return $http.get(spec.url, { transformResponse: [] }).then(function (resp) {
                return { name: spec.filename, text: resp.data };
            });
        })).then(function (entries) {
            downloadBlob(new Blob(makeZip(entries), { type: 'application/zip' }),
                         'domas_example_' + format + '.zip');
        }).catch(function () {
            $scope.exampleAlert = 'Could not read the example files. Check that the '
                + 'domas_examples files were copied into client/resources.';
            $scope.$applyAsync();
        });
    };

    $scope.exampleFormats = [
        { value: 'leafcutter', label: 'LeafCutter' },
        { value: 'rmats', label: 'rMATS' },
        { value: 'majiq', label: 'MAJIQ' }
    ];
    $scope.exampleFormat = 'leafcutter';

    $scope.exampleLoading = false;
    $scope.exampleAlert = '';
    $scope.exampleColumns = [];
    $scope.exampleRows = [];
    $scope.exampleTotalRows = 0;
    $scope.exampleClusterCount = 0;
    $scope.exampleTruncated = false;
    $scope.exampleSummaryText = '';
    $scope.exampleNonComparedText = '';
    $scope.exampleShowSummary = false;

    var exampleCsvText = '';

    self.runExample = function () {
        var specs = EXAMPLES[$scope.exampleFormat];
        if (!specs) return;

        $scope.exampleAlert = '';
        $scope.exampleColumns = [];
        $scope.exampleRows = [];
        $scope.exampleShowSummary = false;
        $scope.exampleLoading = true;

        var fetches = specs.map(function (spec) {
            // plain static text files - no transform, keep the raw body as-is
            return $http.get(spec.url, { transformResponse: [] }).then(function (resp) {
                return { spec: spec, text: resp.data };
            });
        });

        Promise.all(fetches).then(function (results) {
            var files = results.map(function (r) {
                return { name: r.spec.filename, role: r.spec.role, content: utf8ToBase64(r.text) };
            });
            return webService.runDomas({
                format: $scope.exampleFormat,
                specie: 'human',   // every bundled example is real human data
                files: files
            });
        }).then(function (response) {
            $scope.exampleLoading = false;
            exampleCsvText = response.data.csv || '';
            $scope.exampleSummaryText = response.data.summary || '';
            $scope.exampleNonComparedText = response.data.nonCompared || '';
            var summary = summarizeCsv(exampleCsvText);
            if (!summary) {
                $scope.exampleAlert = "DOMAS produced no results for this example.";
            } else {
                $scope.exampleColumns = summary.columns;
                $scope.exampleRows = summary.rows;
                $scope.exampleTotalRows = summary.totalRows;
                $scope.exampleTruncated = summary.truncated;
                $scope.exampleClusterCount = summary.clusterCount;
            }
            $scope.$applyAsync();
        }).catch(function (err) {
            $scope.exampleLoading = false;
            var msg = "Sorry, something went wrong.";
            if (err && err.data && err.data.error) msg = err.data.error;
            else if (err && err.status) msg = "Could not load the example (HTTP " + err.status +
                "). Check that the domas_examples files were copied into client/resources.";
            else if (err && err.message) msg = err.message;
            $scope.exampleAlert = msg;
            $scope.$applyAsync();
        });
    };

    self.downloadExampleResults = function () {
        downloadResults(exampleCsvText, $scope.exampleNonComparedText,
                        $scope.exampleSummaryText, 'domas_example_results.zip');
    };
});
