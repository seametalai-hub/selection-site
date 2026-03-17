# -*- coding: utf-8 -*-
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r'd:\vscode\1688_auto_trial\export_popup_probe.json')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)

    page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      const root = host?.shadowRoot;
      if (!root) throw new Error('NO_HOST');
      const checkbox = root.querySelector('input.ant-checkbox-input');
      if (checkbox && !checkbox.checked) checkbox.click();
    }
    ''')
    page.wait_for_timeout(1200)

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
    page.wait_for_timeout(2000)

    payload = page.evaluate(r'''
    () => {
      const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      const root = host?.shadowRoot || null;
      const collect = (scope, label) => {
        if (!scope) return null;
        const all = Array.from(scope.querySelectorAll('*'));
        const hits = all
          .map((el) => ({
            tag: el.tagName,
            id: el.id || '',
            className: String(el.className || ''),
            text: normalize(el.textContent || ''),
          }))
          .filter((item) => item.text)
          .filter((item) =>
            item.text.includes('导出') ||
            item.text.includes('确认') ||
            item.text.includes('确定') ||
            item.text.includes('取消') ||
            item.text.includes('设置') ||
            item.text.includes('字段') ||
            item.text.includes('主图链接') ||
            item.text.includes('商品链接') ||
            item.text.includes('所在地') ||
            item.text.includes('上架时间') ||
            item.text.includes('店铺名称') ||
            item.text.includes('标题')
          )
          .slice(0, 300);
        const popovers = all
          .filter((el) => String(el.className || '').includes('popover') || String(el.className || '').includes('modal'))
          .map((el) => ({
            tag: el.tagName,
            id: el.id || '',
            className: String(el.className || ''),
            text: normalize(el.textContent || '').slice(0, 500),
          }))
          .slice(0, 80);
        return {label, hits, popovers};
      };
      return {
        shadow: collect(root, 'shadow'),
        document: collect(document, 'document'),
      };
    }
    ''')

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'WROTE={OUT}')
    browser.close()
