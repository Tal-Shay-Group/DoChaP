/**
 * DOMAS page controller.
 *
 * Reads the user-selected input file(s), base64-encodes them in the browser,
 * POSTs them to the server (which runs domas.py on the first 100 clusters),
 * then renders the returned results CSV as a table and offers it for download.
 *
 * Also drives a self-contained "Try it with sample data" panel: its own
 * format selector and its own input/output display, entirely independent of
 * the manual-upload state above. One click (runExample) fetches a bundled
 * example dataset, shows it, POSTs it through the exact same /domas/process
 * endpoint a real upload uses, and renders the results - no server-side
 * change needed for this. The example files are plain static assets under
 * client/resources/domas_examples/.
 */
angular.module("DoChaP").controller('domasController', function ($scope, $http, webService) {
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

    var csvText = '';                 // full CSV, kept for download
    var MAX_DISPLAY_ROWS = 500;       // cap table rows for responsiveness

    // columns whose values are always short - render them narrow
    var NARROW_COLUMNS = {
        canonical_domain_length: true, alternative_domain_length: true,
        canonical_domains_number: true, alternative_domains_number: true,
        is_longest_cds: true, is_most_like_canonical: true
    };
    $scope.isNarrow = function (col) { return NARROW_COLUMNS[col] === true; };

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

    self.download = function () {
        var blob = new Blob([csvText], { type: 'text/csv' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'domas_results.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
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
              label: 'Cluster significance (example, 56 clusters)',
              url: 'resources/domas_examples/leafcutter/leafcutter_ds_cluster_significance.example.txt' },
            { role: 'lc_effect', filename: 'leafcutter_ds_effect_sizes.txt',
              label: 'Effect sizes (example, matching junctions)',
              url: 'resources/domas_examples/leafcutter/leafcutter_ds_effect_sizes.example.txt' }
        ],
        rmats: [
            { role: 'input', filename: 'SE.MATS.JC.txt',
              label: 'SE.MATS.JC.txt (example, 199 events)',
              url: 'resources/domas_examples/rmats/SE.MATS.JC.txt' }
        ],
        majiq: [
            { role: 'input', filename: 'NveB_Mono_voila.txt',
              label: 'MAJIQ voila TSV (example, 199 LSVs)',
              url: 'resources/domas_examples/majiq/NveB_Mono_voila.example.txt' }
        ]
    };

    $scope.exampleFormats = [
        { value: 'leafcutter', label: 'LeafCutter' },
        { value: 'rmats', label: 'rMATS' },
        { value: 'majiq', label: 'MAJIQ' }
    ];
    $scope.exampleFormat = 'leafcutter';

    $scope.exampleLoading = false;
    $scope.exampleAlert = '';
    $scope.exampleFiles = [];       // [{label, text}] - the input preview
    $scope.exampleColumns = [];
    $scope.exampleRows = [];
    $scope.exampleTotalRows = 0;
    $scope.exampleClusterCount = 0;
    $scope.exampleTruncated = false;

    var exampleCsvText = '';

    self.runExample = function () {
        var specs = EXAMPLES[$scope.exampleFormat];
        if (!specs) return;

        $scope.exampleAlert = '';
        $scope.exampleFiles = [];
        $scope.exampleColumns = [];
        $scope.exampleRows = [];
        $scope.exampleLoading = true;

        var fetches = specs.map(function (spec) {
            // plain static text files - no transform, keep the raw body as-is
            return $http.get(spec.url, { transformResponse: [] }).then(function (resp) {
                return { spec: spec, text: resp.data };
            });
        });

        Promise.all(fetches).then(function (results) {
            // show the input right away, before the (slower) DOMAS run finishes
            $scope.exampleFiles = results.map(function (r) { return { label: r.spec.label, text: r.text }; });
            $scope.$applyAsync();

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

    self.downloadExample = function () {
        var blob = new Blob([exampleCsvText], { type: 'text/csv' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'domas_example_results.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };
});
