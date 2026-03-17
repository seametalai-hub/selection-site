# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import sync_playwright

STATE = Path(r'd:\vscode\1688_auto_trial\checkbox_click_probe.txt')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)
    result_before = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      const root = host?.shadowRoot;
      if (!root) return {error: 'NO_HOST'};
      return {
        checked: !!root.querySelector('input.ant-checkbox-input')?.checked,
        labels: Array.from(root.querySelectorAll('label')).map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim()).slice(0, 5)
      };
    }
    ''')
    click_state = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      const root = host?.shadowRoot;
      if (!root) return 'NO_HOST';
      const input = root.querySelector('input.ant-checkbox-input');
      if (!input) return 'NO_INPUT';
      input.click();
      return 'CLICKED_INPUT';
    }
    ''')
    page.wait_for_timeout(2000)
    result_after = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      const root = host?.shadowRoot;
      if (!root) return {error: 'NO_HOST'};
      return {
        checked: !!root.querySelector('input.ant-checkbox-input')?.checked,
        labels: Array.from(root.querySelectorAll('label')).map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim()).slice(0, 5)
      };
    }
    ''')
    STATE.write_text(f'BEFORE={result_before}\nACTION={click_state}\nAFTER={result_after}', encoding='utf-8')
    print(f'WROTE={STATE}')
    browser.close()
