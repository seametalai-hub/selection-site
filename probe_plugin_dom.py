# -*- coding: utf-8 -*-
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r'd:\vscode\1688_auto_trial\plugin_dom_probe.json')
URL = 'http://127.0.0.1:9222'

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(URL)
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)

    main_info = page.evaluate(r'''
    () => {
      const nodes = Array.from(document.querySelectorAll('*'));
      const shadowHosts = nodes
        .filter((el) => el.shadowRoot)
        .map((el) => ({
          tag: el.tagName,
          id: el.id || '',
          className: String(el.className || ''),
          text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 200)
        }));
      const likelyExport = nodes
        .filter((el) => ((el.textContent || '').includes('导出表格') || (el.textContent || '').includes('采购助手') || (el.textContent || '').includes('批量操作')))
        .slice(0, 100)
        .map((el) => ({
          tag: el.tagName,
          id: el.id || '',
          className: String(el.className || ''),
          text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 300)
        }));
      const iframes = Array.from(document.querySelectorAll('iframe')).map((el) => ({
        id: el.id || '',
        name: el.name || '',
        className: String(el.className || ''),
        src: el.src || ''
      }));
      return { shadowHosts, likelyExport, iframes, title: document.title };
    }
    ''')

    frame_info = []
    for frame in page.frames:
        try:
            text = frame.evaluate(r'''
            () => ({
              url: location.href,
              title: document.title || '',
              body: (document.body?.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 2000),
              hits: Array.from(document.querySelectorAll('*'))
                .filter((el) => ((el.textContent || '').includes('导出表格') || (el.textContent || '').includes('采购助手') || (el.textContent || '').includes('批量操作')))
                .slice(0, 50)
                .map((el) => ({
                  tag: el.tagName,
                  id: el.id || '',
                  className: String(el.className || ''),
                  text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 300)
                }))
            })
            ''')
            frame_info.append(text)
        except Exception as exc:
            frame_info.append({"url": frame.url, "error": str(exc)})

    payload = {"main": main_info, "frames": frame_info}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'WROTE={OUT}')
    browser.close()
