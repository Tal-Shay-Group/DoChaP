/**
 * DOMAS integration: receives uploaded splicing-tool output files, runs
 * DOMAS (domas.py) against the local DoChaP DB, and returns the results CSV.
 *
 * The browser can't hand the server a filesystem path, so the client uploads
 * each file's contents (base64) in the POST body; we write them to a private
 * temp directory, run domas.py pointed at that directory, read results.csv,
 * and clean up. Only MAX_CLUSTERS clusters are processed - the most significant
 * ones the input names; see -max_clusters in domas.py.
 */
const express = require("express");
const router = express.Router();
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

// --- configuration ---------------------------------------------------------
// Absolute path to domas.py and the python interpreter that has DOMAS's deps
// (pandas, openpyxl, numpy, sqlite3). DOMAS lives outside this repo and its
// location differs per install, so it comes from the environment when
// possible. The default below is a sibling checkout layout and intentionally
// avoids a developer-specific machine path.
const DEFAULT_DOMAS_PATH = path.resolve(__dirname, "..", "DOMAS", "code", "domas.py");
const DOMAS_PATH = process.env.DOMAS_PATH || DEFAULT_DOMAS_PATH;
const DOMAS_PY = resolveDomasPy(DOMAS_PATH);

function resolvePythonExecutable() {
    if (process.env.DOMAS_PYTHON) {
        return process.env.DOMAS_PYTHON;
    }
    return process.platform === "win32" ? "py" : "python3";
}

const PYTHON = resolvePythonExecutable();

// Accept a directory for DOMAS_PATH too - pointing at the DOMAS checkout or its
// code/ dir is the natural mistake, and failing on it would only surface later
// as a python "can't open file" error.
function resolveDomasPy(p) {
    let stat;
    try { stat = fs.statSync(p); } catch (e) { return p; }  // reported at run time
    if (!stat.isDirectory()) return p;
    const candidates = [path.join(p, "domas.py"), path.join(p, "code", "domas.py")];
    return candidates.find((c) => fs.existsSync(c)) || path.join(p, "domas.py");
}
// The summary names the input file it was given, which here is a path inside
// this request's private temp directory - a detail of how the server works and
// nothing the browser should be shown. Reduced to the bare filenames, which is
// what the user recognises anyway.
function stripWorkDir(text, workDir) {
    if (!text) return "";
    return text.split(workDir + path.sep).join("").split(workDir).join("");
}

// DoChaP DB lives alongside this server file.
const DOCHAP_DB = path.resolve(__dirname, "DB_merged.sqlite");
const MAX_CLUSTERS = 100;
const NUM_WORKERS = 2;
// domas.py also accepts 'hadas', but that is a bulk human/mouse comparison
// table driven from the CLI, not something this page offers.
const VALID_FORMATS = ["leafcutter", "rmats", "majiq", "ioe"];
// domas.py requires -species for all of these: none of the formats above carry
// a species field.
const VALID_SPECIES = ["human", "mouse", "rat"];

router.post("/domas/process", (req, res) => {
    const { format, specie, files } = req.body || {};

    // --- validate ---
    if (!VALID_FORMATS.includes(format)) {
        return res.status(400).json({ error: "Invalid or missing format." });
    }
    if (!VALID_SPECIES.includes(specie)) {
        return res.status(400).json({
            error: "Please choose a species (" + VALID_SPECIES.join(", ") + ") for format " + format + ".",
        });
    }
    if (!Array.isArray(files) || files.length === 0) {
        return res.status(400).json({ error: "No input files were provided." });
    }
    if (!fs.existsSync(DOMAS_PY)) {
        return res.status(500).json({
            error: "DOMAS is not installed at " + DOMAS_PY +
                   ". Set the DOMAS_PATH environment variable to domas.py (or the directory holding it).",
        });
    }

    // --- write uploaded files into a private temp dir ---
    const workDir = fs.mkdtempSync(path.join(os.tmpdir(), "domas-"));
    const cleanup = () => {
        try { fs.rmSync(workDir, { recursive: true, force: true }); } catch (e) { /* ignore */ }
    };

    let byRole = {};   // role -> absolute path
    try {
        for (const f of files) {
            if (!f || typeof f.name !== "string" || typeof f.content !== "string") {
                throw new Error("Malformed file entry in request.");
            }
            const safeName = path.basename(f.name); // guard against path traversal
            const dest = path.join(workDir, safeName);
            fs.writeFileSync(dest, Buffer.from(f.content, "base64"));
            byRole[f.role || "input"] = dest;
        }
    } catch (e) {
        cleanup();
        return res.status(400).json({ error: "Could not save uploaded files: " + e.message });
    }

    // --- build domas.py arguments per format ---
    // The page runs domas.py with its OWN defaults: no option that changes what
    // the analysis does is passed from here. Everything below is plumbing the
    // CLI cannot infer - where the database is, which species, which format,
    // where to write - plus two server-side resource limits. PDFs are opt-in on
    // domas.py's side (-pdf), so nothing is needed to suppress them.
    const args = [
        DOMAS_PY,
        "-dochap", DOCHAP_DB,
        "-max_clusters", String(MAX_CLUSTERS),
        "-num_workers", String(NUM_WORKERS),
        "-output_csv", path.join(workDir, "results.csv"),
        // domas.py saves its results as .xlsx by default. This server reads the
        // result back and sends it to the page as text, so it asks for the CSV
        // instead - the browser builds the workbook the Download button hands
        // over, from the same rows it is already displaying.
        "-no_excel",
    ];
    args.push("-species", specie);

    try {
        if (format === "leafcutter") {
            if (!byRole.lc_sig || !byRole.lc_effect) {
                throw new Error("leafcutter needs both a cluster-significance file and an effect-sizes file.");
            }
            args.push("-format", "leafcutter", "-lc_sig", byRole.lc_sig, "-lc_effect", byRole.lc_effect);
        } else if (format === "rmats") {
            // the (up to five) MATS.JC.txt files all live in workDir
            args.push("-format", "rmats", "-input", workDir);
        } else {
            // majiq / ioe: a single input file
            const only = byRole.input || Object.values(byRole)[0];
            if (!only) throw new Error("No input file found for format " + format + ".");
            args.push("-format", format, "-input", only);
        }
    } catch (e) {
        cleanup();
        return res.status(400).json({ error: e.message });
    }

    // --- run domas.py (async, so we don't block the event loop) ---
    const csvPath = path.join(workDir, "results.csv");
    // domas.py writes two more files beside the results CSV, both named after
    // it (see junction_analisys.summary_path / non_compared_path): a run
    // summary - what the input held, how much of it reached a comparison, and
    // why the rest did not - and the rows that never reached a comparison,
    // each naming its reason. The browser offers all three as one download.
    const summaryPath = path.join(workDir, "results_summary.txt");
    const nonComparedPath = path.join(workDir, "non_results.csv");
    let stderr = "";
    let responded = false;
    const finish = (status, body) => {
        if (responded) return;
        responded = true;
        cleanup();
        res.status(status).json(body);
    };

    const py = spawn(PYTHON, args, { cwd: workDir });
    py.stderr.on("data", (d) => { stderr += d.toString(); });
    py.on("error", (err) => {
        finish(500, { error: "Failed to start " + PYTHON + ": " + err.message });
    });
    py.on("close", (code) => {
        if (code !== 0 || !fs.existsSync(csvPath)) {
            const tail = stderr.trim().split("\n").slice(-8).join("\n");
            return finish(500, {
                error: "DOMAS failed (exit " + code + ").\n" + (tail || "no error output"),
            });
        }
        let csv;
        try {
            csv = fs.readFileSync(csvPath, "utf-8");
        } catch (e) {
            return finish(500, { error: "Could not read results: " + e.message });
        }
        // Both companions are nice-to-haves: a run that produced a CSV
        // succeeded, so either one missing is reported as absent rather than
        // failing the request.
        const optional = (p) => {
            try { return fs.readFileSync(p, "utf-8"); } catch (e) { return ""; }
        };
        finish(200, {
            csv: csv,
            summary: stripWorkDir(optional(summaryPath), workDir),
            nonCompared: optional(nonComparedPath),
        });
    });
});

module.exports = router;
