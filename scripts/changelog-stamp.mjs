#!/usr/bin/env node
/**
 * Appends a dated "Build" block under ## [Unreleased] in CHANGELOG.md
 * with commit subjects since `.changelog-last-ref` (full SHA of last stamp).
 *
 * Usage (repo root):
 *   pnpm changelog:stamp
 *   CHANGELOG_NOTE="Fixed radar tiles" pnpm changelog:stamp
 *
 * Commit CHANGELOG.md + .changelog-last-ref after each stamp you want in history.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { execFileSync } from "node:child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const markerPath = path.join(root, ".changelog-last-ref");
const changelogPath = path.join(root, "CHANGELOG.md");
const pkgPath = path.join(root, "frontend", "package.json");

const PRETTY = "format:- %s (%h)";

function runGit(args) {
  return execFileSync("git", args, { cwd: root, encoding: "utf8" }).trim();
}

let pkg;
try {
  pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
} catch {
  console.error("changelog-stamp: missing or invalid frontend/package.json");
  process.exit(1);
}

const version = pkg.version || "0.0.0";
let head;
try {
  head = runGit(["rev-parse", "HEAD"]);
} catch {
  console.error("changelog-stamp: not a git repository or git failed");
  process.exit(1);
}

let fromSha = "";
if (fs.existsSync(markerPath)) {
  const raw = fs.readFileSync(markerPath, "utf8").trim().split(/\s+/)[0] || "";
  if (/^[0-9a-f]{7,40}$/i.test(raw) && !/^0+$/.test(raw)) fromSha = raw;
}

let logLines = [];
if (fromSha) {
  try {
    const raw = runGit(["log", `${fromSha}..HEAD`, `--pretty=${PRETTY}`, "--no-merges"]);
    logLines = raw ? raw.split("\n").filter(Boolean) : [];
  } catch {
    logLines = [];
  }
  if (!logLines.length) {
    logLines = ["- _(no new commits since last stamp)_"];
  }
} else {
  const raw = runGit(["log", "-15", `--pretty=${PRETTY}`, "--no-merges"]);
  logLines = raw ? raw.split("\n").filter(Boolean) : ["- _(no commits found)_"];
}

const extra = process.env.CHANGELOG_NOTE
  ? `\n- ${String(process.env.CHANGELOG_NOTE).trim().replace(/\n/g, "\n- ")}`
  : "";

const stamp = new Date().toISOString().slice(0, 19) + "Z";
const block = `\n### Build ${stamp} - frontend v${version}\n\n${logLines.join("\n")}${extra}\n\n`;

let md = fs.readFileSync(changelogPath, "utf8");
const unreleased = "## [Unreleased]";
if (!md.includes(unreleased)) {
  console.error("changelog-stamp: CHANGELOG.md must contain", unreleased);
  process.exit(1);
}

// Newest build first: insert right after the [Unreleased] heading (before ### Added / etc.)
md = md.replace(/^(## \[Unreleased\]\s*\r?\n)/m, `$1${block}`);
fs.writeFileSync(changelogPath, md);
fs.writeFileSync(markerPath, `${head}\n`);

console.log(`changelog-stamp: wrote ${logLines.length} line(s); marker -> ${head.slice(0, 7)}`);
console.log(`changelog-stamp: edit CHANGELOG.md if you want to group under Added/Fixed, then commit.`);
