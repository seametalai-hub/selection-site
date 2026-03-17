# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path(r'd:\vscode\1688_auto_trial\downloads')
OUT_DIR.mkdir(parents=True, exist_ok=True)
STATE = Path(r'd:\vscode\1688_auto_trial\shadow_select_all_export.txt')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)

    logs = []

    click_all = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      if (!host || !host.shadowRoot) return 'NO_HOST';
      const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const target = Array.from(host.shadowRoot.querySelectorAll('label,span,button,div'))
        .find((el) => normalize(el.textContent).includes('全选['));
      if (!target) return 'NO_SELECT_ALL';
      target.click();
      return normalize(target.textContent);
    }
    ''')
    logs.append(f'SELECT_ALL={click_all}')
    page.wait_for_timeout(2000)

    counts = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      if (!host || !host.shadowRoot) return ['NO_HOST'];
      return Array.from(host.shadowRoot.querySelectorAll('*'))
        .map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim())
        .filter(Boolean)
        .filter((t) => t.includes('全选[') || t.includes('有销量[') || t.includes('自定义['))
        .slice(0, 20);
    }
    ''')
    logs.extend([f'COUNT={c}' for c in counts])

    try:
        with page.expect_download(timeout=20000) as dl_info:
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
        logs.append(f'DOWNLOADED={target}')
    except Exception as exc:
        logs.append(f'DOWNLOAD_FAILED={type(exc).__name__}: {exc}')
        modal_texts = page.evaluate(r'''
        () => {
          const host = document.querySelector('#market-mate-offer-list-toolbar');
          const roots = [];
          if (host?.shadowRoot) roots.push(host.shadowRoot);
          roots.push(document);
          const acc = [];
          for (const root of roots) {
            const els = Array.from(root.querySelectorAll('*'));
            for (const el of els) {
              const t = (el.textContent || '').replace(/\s+/g, ' ').trim();
              if (!t) continue;
              if (t.includes('导出') || t.includes('设置') || t.includes('字段') || t.includes('标题') || t.includes('所在地') || t.includes('商品链接') || t.includes('主图链接') || t.includes('上架时间') || t.includes('店铺名称')) {
                acc.push(t.slice(0, 400));
              }
            }
          }
          return acc.slice(0, 120);
        }
        ''')
        logs.extend([f'TEXT={t}' for t in modal_texts])

    STATE.write_text('\n'.join(logs), encoding='utf-8')
    print(f'WROTE={STATE}')
    browser.close()
