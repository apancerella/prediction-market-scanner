// Builds a single self-contained HTML page of the dashboard, with the scan data embedded,
// for publishing as a Claude artifact. Run after `npm run build`:
//   node scripts/build-artifact.mjs <data-dir> <out.html>
// <data-dir> holds latest.json, picks.json and (optionally) opinions.json from the data branch.
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const [dataDir, outFile] = process.argv.slice(2);
if (!dataDir || !outFile) {
  console.error("usage: node scripts/build-artifact.mjs <data-dir> <out.html>");
  process.exit(1);
}
const dist = resolve(import.meta.dirname, "..", "dist");
const html = readFileSync(join(dist, "index.html"), "utf8");
const jsPath = html.match(/<script[^>]+src="\.?\/?([^"]+\.js)"/)?.[1];
const cssPath = html.match(/<link[^>]+href="\.?\/?([^"]+\.css)"/)?.[1];
if (!jsPath || !cssPath) throw new Error("Couldn't find the built JS/CSS in dist/index.html; run `npm run build` first");
const js = readFileSync(join(dist, jsPath), "utf8");
const css = readFileSync(join(dist, cssPath), "utf8");

const load = (name) => {
  const p = join(dataDir, `${name}.json`);
  return existsSync(p) ? JSON.parse(readFileSync(p, "utf8")) : null;
};
const latest = load("latest");
const picks = load("picks");
const opinions = load("opinions");

// Keep the page small: price history only for current picks, plus settled picks for the track record.
if (picks && latest) {
  const live = new Set(latest.opportunities.map((o) => o.id));
  for (const [id, p] of Object.entries(picks.picks)) {
    if (live.has(id)) continue;
    if (p.result) p.samples = [];
    else delete picks.picks[id];
  }
}

const safe = (s) => s.replace(/<\/(script|style)/gi, "<\\/$1");
const data = JSON.stringify({ latest, picks, opinions }).replace(/</g, "\\u003c");

const page = `<title>Prediction Market Scanner</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>${safe(css)}</style>
<div id="root"></div>
<script>window.__PMS_DATA__ = ${data};</script>
<script type="module">${safe(js)}</script>
`;
writeFileSync(outFile, page);
console.log(`Wrote ${outFile} (${(page.length / 1024).toFixed(0)} KB, ${latest?.opportunities.length ?? 0} picks, ` +
  `opinions: ${opinions ? "yes" : "none"})`);
