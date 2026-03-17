# -*- coding: utf-8 -*-
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r'd:\vscode\1688_auto_trial\plugin_shadow_probe.json')
URL = 'http://127.0.0.1:9222'
SELECTORS = ['buyer-workbench', '#market-mate-offer-list-toolbar', 'channel-toolbox-batch-distribute-pro']

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(URL)
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)
    result = {}
    for sel in SELECTORS:
        try:
            data = page.evaluate(r'''
            ([selector]) => {
              const el = document.querySelector(selector);
              if (!el) return {found: false};
              const root = el.shadowRoot;
              if (!root) return {found: true, hasShadow: false, tag: el.tagName, id: el.id || '', className: String(el.className || '')};
              const texts = Array.from(root.querySelectorAll('*'))
                .map((node) => (node.textContent || '').replace(/\s+/g, ' ').trim())
                .filter(Boolean);
              const hits = Array.from(root.querySelectorAll('*'))
                .filter((node) => {
                  const t = (node.textContent || '').replace(/\s+/g, ' ').trim();
                  return t.includes('导出表格') || t.includes('采购助手') || t.includes('批量操作') || t.includes('商品选择') || t.includes('全选') || t.includes('有销量');
                })
                .slice(0, 200)
                .map((node) => ({
                  tag: node.tagName,
                  id: node.id || '',
                  className: String(node.className || ''),
                  text: (node.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 300)
                }));
              return {
                found: true,
                hasShadow: true,
                tag: el.tagName,
                id: el.id || '',
                className: String(el.className || ''),
                texts: texts.slice(0, 300),
                hits,
              };
            }
            ''', [sel])
            result[sel] = data
        except Exception as exc:
            result[sel] = {'error': str(exc)}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'WROTE={OUT}')
    browser.close()
