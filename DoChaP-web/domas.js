/**
 * DOMAS integration: receives uploaded splicing-tool output files, runs
 * DOMAS (domas.py) against the local DoChaP DB, and returns the results CSV.
 *
 * The browser can't hand the server a filesystem path, so the client uploads
 * each file's contents (base64) in the POST body; we write them to a private
 * temp directory, run domas.py pointed at that directory, read results.csv,
 * and clean up. Only the first MAX_CLUSTERS clusters are processed.
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
// location differs per install, so it comes from the environment: DOMAS_PATH
// is either domas.py itself or the directory holding it. The default below is
// only the development layout.
const DOMAS_PATH = process.env.DOMAS_PATH ||
    "/Users/arielmelchior/Documents/projects/DOMAS/code/domas.py";
const DOMAS_PY = resolveDomasPy(DOMAS_PATH);
const PYTHON = process.env.DOMAS_PYTHON || "python3";

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
// DoChaP DB lives alongside this server file.
const DOCHAP_DB = path.resolve(__dirname, "DB_merged.sqlite");
const MAX_CLUSTERS = 100;
const NUM_WORKERS = 2;
const VALID_FORMATS = ["leafcutter", "rmats", "majiq", "hadas", "ioe"];
// domas.py requires -specie for every format except hadas, which is a
// human/mouse comparison carrying the species per row (and rejects -specie).
const VALID_SPECIES = ["human", "mouse", "rat"];

router.post("/domas/process", (req, res) => {
    const { format, specie, files, useRepDomains, filterNonComparable } = req.body || {};

    // --- validate ---
    if (!VALID_FORMATS.includes(format)) {
        return res.status(400).json({ error: "Invalid or missing format." });
    }
    if (format !== "hadas" && !VALID_SPECIES.includes(specie)) {
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
    // PDFs are opt-in on domas.py's side (-pdf), so nothing is needed to
    // suppress them here. Representative domains and the non-comparable filter
    // are both on by default there, so only the "off" case is passed on.
    const args = [
        DOMAS_PY,
        "-dochap", DOCHAP_DB,
        "-max_clusters", String(MAX_CLUSTERS),
        "-num_workers", String(NUM_WORKERS),
        "-output_csv", path.join(workDir, "results.csv"),
    ];
    if (format !== "hadas") args.push("-specie", specie);
    if (!useRepDomains) args.push("-no_representative_domains");
    if (!filterNonComparable) args.push("-keep_non_comparable");

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
            // majiq / hadas / ioe: a single input file
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
        finish(500, { error: "Failed to start python3: " + err.message });
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
        finish(200, { csv: csv });
    });
});

module.exports = router;
