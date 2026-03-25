# CLI Workflow

## Unified Entry

Primary one-click command:

```powershell
run_live_update.bat
```

This is the daily operator entrypoint.

It will:
- scrape all enabled categories
- keep only `<= 7天` rows
- stop when the page tail has clearly entered `> 7天`
- generate `products.json`
- rebuild and publish the local site
- commit and push to GitHub
- let Vercel refresh the public link

Manual CLI entrypoint:

```powershell
python update_products.py run --stop-days 7
```

## Commands

```powershell
python update_products.py estimate
python update_products.py scrape --stop-days 7
python update_products.py generate-json --run-dir <run_dir>
python update_products.py build-site --run-dir <run_dir>
python update_products.py publish --run-dir <run_dir>
python update_products.py package --run-dir <run_dir>
python update_products.py report --run-dir <run_dir>
python update_products.py run --stop-days 7
```

## Category Config

Category config file:

[categories.json](./categories.json)

Current scope:
- 12 categories
- in `--stop-days 7` mode, category `target_items` is treated as a legacy config value and not used as a hard cap
- excludes `电动车` and `整车`

## Output Structure

```text
outputs/
  YYYY-MM-DD/
    run-HHMMSS/
      manifest.json
      summary.json
      products.json
      raw/
        <category>.csv
      site/
        index.html
        products.html
        styles.css
        app.js
        data.js
        products.json
      package/
        demo/
        demo-YYYY-MM-DD-run-HHMMSS.zip
```

## Runtime Estimate

Current estimate for full 12-category `7天` mode:
- optimistic: about 27 minutes
- conservative: about 51 minutes
- external communication recommendation: 30 to 60 minutes

Estimate source command:

```powershell
python update_products.py estimate
```

## OpenClaw Integration Placeholder

Recommended OpenClaw call:

```powershell
run_live_update.bat
```

Expected reply payload fields:
- run_dir
- category_count
- scraped_total
- deduped_rows
- duration_total_seconds
- package

## Smoke Test Status

Verified locally:
- `python update_products.py scrape --categories d:\vscode\categories.test.json --target-date 2026-03-16 --run-label cli-smoke --headless`
- `python update_products.py run --categories d:\vscode\categories.test.json --target-date 2026-03-16 --run-label cli-run-smoke --headless`
