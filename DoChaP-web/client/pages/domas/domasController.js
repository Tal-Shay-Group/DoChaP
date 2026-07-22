/**
 * DOMAS page controller.
 *
 * Reads the user-selected input file(s), base64-encodes them in the browser,
 * POSTs them to the server (which runs domas.py on the first 100 clusters),
 * then renders the returned results CSV as a table and offers it for download.
 */
angular.module("DoChaP").controller('domasController', function ($scope, webService) {
    var self = this;

    // dropdown options; leafcutter is the default
    $scope.formats = [
        { value: 'leafcutter', label: 'LeafCutter' },
        { value: 'rmats', label: 'rMATS' },
        { value: 'majiq', label: 'MAJIQ' },
        { value: 'hadas', label: 'Hadas' },
        { value: 'ioe', label: 'SUPPA (ioe)' }
    ];
    $scope.format = 'leafcutter';
    $scope.filterNonComparable = true;   // only comparable transcripts, on by default

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
        c_domain_length: true, t_domain_length: true,
        c_domains_number: true, t_domains_number: true,
        is_longest_cds: true, is_most_like_canonical: true
    };
    $scope.isNarrow = function (col) { return NARROW_COLUMNS[col] === true; };

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
        // majiq / hadas / ioe: single file
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

        // read the shared 'representative domains' checkbox from the top bar
        var useRepDomains = sessionStorage.getItem("useRepDomains") !== "false";

        $scope.loading = true;
        Promise.all(reads).then(function (files) {
            return webService.runDomas({
                format: $scope.format,
                useRepDomains: useRepDomains,
                filterNonComparable: $scope.filterNonComparable === true,
                files: files
            });
        }).then(function (response) {
            $scope.loading = false;
            renderCsv(response.data.csv);
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

    function renderCsv(csv) {
        csvText = csv || '';
        var parsed = parseCsv(csvText).filter(function (r) { return r.length > 1 || (r.length === 1 && r[0] !== ''); });
        if (parsed.length === 0) {
            $scope.alert = "DOMAS produced no results for this input.";
            return;
        }
        $scope.columns = parsed[0];
        var body = parsed.slice(1);
        $scope.totalRows = body.length;
        $scope.truncated = body.length > MAX_DISPLAY_ROWS;
        $scope.rows = body.slice(0, MAX_DISPLAY_ROWS);

        // count distinct clusters (the 'cluster' column, if present)
        var cidx = $scope.columns.indexOf('cluster');
        if (cidx === -1) cidx = $scope.columns.indexOf('cluster_name');
        if (cidx !== -1) {
            var seen = {};
            body.forEach(function (r) { seen[r[cidx]] = true; });
            $scope.clusterCount = Object.keys(seen).length;
        } else {
            $scope.clusterCount = '?';
        }
    }

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
});
