# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import sync_playwright

STATE = Path(r'd:\vscode\1688_auto_trial\toolbar_input_probe.txt')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)
    result = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      if (!host || !host.shadowRoot) return {error: 'NO_HOST'};
      const root = host.shadowRoot;
      const checkbox = root.querySelector('input.ant-checkbox-input');
      const radios = Array.from(root.querySelectorAll('input.ant-radio-input')).map((el, idx) => ({idx, checked: el.checked}));
      const labels = Array.from(root.querySelectorAll('label')).map((el, idx) => ({idx, text: (el.textContent || '').replace(/\s+/g, ' ').trim()})).slice(0, 20);
      return {
        checkboxExists: !!checkbox,
        checkboxChecked: checkbox ? checkbox.checked : null,
        radios,
        labels,
      };
    }
    ''')
    STATE.write_text(str(result), encoding='utf-8')
    print(f'WROTE={STATE}')
    browser.close()
