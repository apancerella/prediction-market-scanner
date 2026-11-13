---
name: publish-artifact
description: Rebuild the dashboard as a single self-contained page with the latest data embedded and republish it to the user's Claude artifact (same URL every time). Run at the end of every daily review, or when the user asks to refresh the Claude version of the app.
---

# Publish the dashboard to Claude

Artifact URL (always update this one; never create a new one):
**https://claude.ai/artifact/YQzrDcWQSEPMtHqzxsHk35**

Artifacts can't fetch data from other sites, so each publish is a snapshot with the data built in.

1. Collect the latest data from the `data` branch (include opinions.json if you just wrote one):
   ```bash
   cd <repo root>
   git fetch -q origin data
   mkdir -p /tmp/pms-data
   for f in latest picks opinions; do git show origin/data:$f.json > /tmp/pms-data/$f.json 2>/dev/null || rm -f /tmp/pms-data/$f.json; done
   ```
2. Build the page:
   ```bash
   cd web && npm ci --no-audit --no-fund && npm run build
   node scripts/build-artifact.mjs /tmp/pms-data /tmp/pms-artifact.html
   ```
3. With the Artifact tool, first `read` the URL above (required before updating an artifact from a new
   session), then `publish` with `file_path: /tmp/pms-artifact.html` and `url` set to the URL above.
   Don't pass `icon`. Keep the title as is.
4. If the publish is refused because the live version changed, publish again from the same file (the page is
   generated, so there's nothing to merge). If the Artifact tool isn't available in this session, say so in
   the summary; the GitHub Pages dashboard still updates.
