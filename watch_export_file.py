# -*- coding: utf-8 -*-
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

DOWNLOAD_DIR = Path.home() / 'Downloads'
PATTERN = '商品列表-1688采购助手*.xlsx'
STATE = Path(r'd:\vscode\1688_auto_trial\export_file_watch.txt')


def latest_matching_file() -> Path | None:
    files = sorted(DOWNLOAD_DIR.glob(PATTERN), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)

    before = latest_matching_file()
    before_mtime = before.stat().st_mtime if before else 0
    logs = [f'BEFORE={before}']

    select_state = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      const root = host?.shadowRoot;
      if (!root) return {error: 'NO_HOST'};
      const input = root.querySelector('input.ant-checkbox-input');
      if (!input) return {error: 'NO_INPUT'};
      if (!input.checked) input.click();
      const btn = Array.from(root.querySelectorAll('button'))
        .find((el) => ((el.textContent || '').replace(/\s+/g, ' ').trim() === '导出表格'));
      return {
        checked: input.checked,
        labels: Array.from(root.querySelectorAll('label')).map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim()).slice(0, 5),
        exportBtnFound: !!btn,
      };
    }
    ''')
    logs.append(f'SELECT_STATE={select_state}')
    page.wait_for_timeout(1000)

    click_state = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      const root = host?.shadowRoot;
      if (!root) return 'NO_HOST';
      const btn = Array.from(root.querySelectorAll('button'))
        .find((el) => ((el.textContent || '').replace(/\s+/g, ' ').trim() === '导出表格'));
      if (!btn) return 'NO_BUTTON';
      btn.click();
      return 'CLICKED';
    }
    ''')
    logs.append(f'CLICK={click_state}')

    found = None
    deadline = time.time() + 30
    while time.time() < deadline:
      latest = latest_matching_file()
      if latest and latest.stat().st_mtime > before_mtime:
          found = latest
          break
      time.sleep(1)

    if found:
        logs.append(f'FOUND={found}')
        logs.append(f'SIZE={found.stat().st_size}')
    else:
        latest = latest_matching_file()
        logs.append(f'FOUND=None')
        logs.append(f'LATEST_NOW={latest}')
        if latest:
            logs.append(f'LATEST_MTIME={latest.stat().st_mtime}')
            logs.append(f'LATEST_SIZE={latest.stat().st_size}')

    STATE.write_text('\n'.join(logs), encoding='utf-8')
    print(f'WROTE={STATE}')
    browser.close()
