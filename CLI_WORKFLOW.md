# CLI Workflow

## Unified Entry

Primary command:

```powershell
python update_products.py run
```

This is the single workflow entrypoint for OpenClaw / manual runs.

## Commands

```powershell
python update_products.py estimate
python update_products.py scrape
python update_products.py generate-json --run-dir <run_dir>
python update_products.py build-site --run-dir <run_dir>
python update_products.py package --run-dir <run_dir>
python update_products.py report --run-dir <run_dir>
python update_products.py run
```

## Category Config

Category config file:

[categories.json](./categories.json)

Current scope:
- 12 categories
- default 500 items per category
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

Current estimate for 12 categories x 500 items:
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
python update_products.py run
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
