# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path(r'd:\vscode\1688_auto_trial\downloads')
OUT_DIR.mkdir(parents=True, exist_ok=True)
STATE = Path(r'd:\vscode\1688_auto_trial\shadow_export_click.txt')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)

    clicked = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      if (!host || !host.shadowRoot) return 'NO_HOST';
      const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const btn = Array.from(host.shadowRoot.querySelectorAll('button,span,div'))
        .find((el) => normalize(el.textContent) === '导出表格');
      if (!btn) return 'NO_BUTTON';
      btn.click();
      return 'CLICKED';
    }
    ''')
    page.wait_for_timeout(2000)

    result = [f'CLICK={clicked}']

    try:
        with page.expect_download(timeout=15000) as dl_info:
            page.evaluate(r'''
            () => {
              const host = document.querySelector('#market-mate-offer-list-toolbar');
              if (!host || !host.shadowRoot) throw new Error('NO_HOST');
              const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
              const btn = Array.from(host.shadowRoot.querySelectorAll('button,span,div'))
                .find((el) => normalize(el.textContent) === '导出表格');
              if (!btn) throw new Error('NO_BUTTON');
              btn.click();
            }
            ''')
        download = dl_info.value
        target = OUT_DIR / download.suggested_filename
        download.save_as(str(target))
        result.append(f'DOWNLOADED={target}')
    except Exception as exc:
        result.append(f'DOWNLOAD_FAILED={type(exc).__name__}: {exc}')
        try:
            texts = page.evaluate(r'''
            () => {
              const host = document.querySelector('#market-mate-offer-list-toolbar');
              if (!host || !host.shadowRoot) return ['NO_HOST'];
              return Array.from(host.shadowRoot.querySelectorAll('*'))
                .map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim())
                .filter(Boolean)
                .filter((t) => t.includes('导出') || t.includes('设置') || t.includes('标题') || t.includes('所在地') || t.includes('商品链接') || t.includes('主图链接'))
                .slice(0, 200);
            }
            ''')
            result.extend([f'TEXT={t}' for t in texts])
        except Exception as inner_exc:
            result.append(f'TEXT_PROBE_FAILED={inner_exc}')

    STATE.write_text('\n'.join(result), encoding='utf-8')
    print(f'WROTE={STATE}')
    browser.close()
