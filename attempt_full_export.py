# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path(r'd:\vscode\1688_auto_trial\downloads')
OUT_DIR.mkdir(parents=True, exist_ok=True)
STATE = Path(r'd:\vscode\1688_auto_trial\full_export_attempt.txt')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)
    logs = []

    select_result = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      const root = host?.shadowRoot;
      if (!root) return {error: 'NO_HOST'};
      const input = root.querySelector('input.ant-checkbox-input');
      if (!input) return {error: 'NO_INPUT'};
      if (!input.checked) input.click();
      const labels = Array.from(root.querySelectorAll('label')).map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim()).slice(0, 5);
      return {checked: input.checked, labels};
    }
    ''')
    logs.append(f'SELECT={select_result}')
    page.wait_for_timeout(1500)

    try:
        with page.expect_download(timeout=25000) as dl_info:
            page.evaluate(r'''
            () => {
              const host = document.querySelector('#market-mate-offer-list-toolbar');
              const root = host?.shadowRoot;
              if (!root) throw new Error('NO_HOST');
              const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
              const btn = Array.from(root.querySelectorAll('button,span,div'))
                .find((el) => normalize(el.textContent) === '导出表格');
              if (!btn) throw new Error('NO_BUTTON');
              btn.click();
            }
            ''')
        download = dl_info.value
        target = OUT_DIR / download.suggested_filename
        download.save_as(str(target))
        logs.append(f'DOWNLOADED={target}')
    except Exception as exc:
        logs.append(f'DOWNLOAD_FAILED={type(exc).__name__}: {exc}')
        probe = page.evaluate(r'''
        () => {
          const host = document.querySelector('#market-mate-offer-list-toolbar');
          const root = host?.shadowRoot;
          const results = [];
          if (root) {
            results.push(...Array.from(root.querySelectorAll('*'))
              .map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim())
              .filter(Boolean)
              .filter((t) => t.includes('导出') || t.includes('字段') || t.includes('设置') || t.includes('标题') || t.includes('所在地') || t.includes('主图链接') || t.includes('商品链接') || t.includes('上架时间') || t.includes('店铺名称'))
              .slice(0, 120));
          }
          results.push(...Array.from(document.querySelectorAll('*'))
            .map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim())
            .filter(Boolean)
            .filter((t) => t.includes('导出') || t.includes('字段') || t.includes('设置') || t.includes('标题') || t.includes('所在地') || t.includes('主图链接') || t.includes('商品链接') || t.includes('上架时间') || t.includes('店铺名称'))
            .slice(0, 120));
          return results.slice(0, 200);
        }
        ''')
        logs.extend([f'TEXT={t}' for t in probe])

    STATE.write_text('\n'.join(logs), encoding='utf-8')
    print(f'WROTE={STATE}')
    browser.close()
