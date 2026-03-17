# -*- coding: utf-8 -*-
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

DOWNLOAD_DIR = Path.home() / 'Downloads'
PATTERN = '商品列表-1688采购助手*.xlsx'
STATE = Path(r'd:\vscode\1688_auto_trial\real_click_export.txt')


def latest_matching_file() -> Path | None:
    files = sorted(DOWNLOAD_DIR.glob(PATTERN), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.set_viewport_size({"width": 1600, "height": 1200})
    page.wait_for_timeout(1000)

    before = latest_matching_file()
    before_mtime = before.stat().st_mtime if before else 0
    logs = [f'BEFORE={before}']

    rects = page.evaluate(r'''
    () => {
      const host = document.querySelector('#market-mate-offer-list-toolbar');
      const root = host?.shadowRoot;
      if (!root) return {error: 'NO_HOST'};
      const checkbox = root.querySelector('input.ant-checkbox-input');
      const exportBtn = Array.from(root.querySelectorAll('button'))
        .find((el) => ((el.textContent || '').replace(/\s+/g, ' ').trim() === '导出表格'));
      if (!checkbox || !exportBtn) {
        return {error: 'MISSING_CONTROLS', checkbox: !!checkbox, exportBtn: !!exportBtn};
      }
      const checkboxRect = checkbox.getBoundingClientRect();
      const exportRect = exportBtn.getBoundingClientRect();
      const labels = Array.from(root.querySelectorAll('label')).map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim()).slice(0, 5);
      return {
        checkbox: {
          left: checkboxRect.left,
          top: checkboxRect.top,
          width: checkboxRect.width,
          height: checkboxRect.height,
          checked: checkbox.checked,
        },
        exportBtn: {
          left: exportRect.left,
          top: exportRect.top,
          width: exportRect.width,
          height: exportRect.height,
          text: (exportBtn.textContent || '').replace(/\s+/g, ' ').trim(),
        },
        labels,
      };
    }
    ''')
    logs.append(f'RECTS={rects}')

    if isinstance(rects, dict) and 'error' not in rects:
        cb = rects['checkbox']
        btn = rects['exportBtn']
        cbx = cb['left'] + cb['width'] / 2
        cby = cb['top'] + cb['height'] / 2
        bx = btn['left'] + btn['width'] / 2
        by = btn['top'] + btn['height'] / 2

        if not cb['checked']:
            page.mouse.move(cbx - 20, cby)
            page.wait_for_timeout(100)
            page.mouse.move(cbx, cby, steps=10)
            page.mouse.down()
            page.wait_for_timeout(80)
            page.mouse.up()
            page.wait_for_timeout(1500)

        labels_after_select = page.evaluate(r'''
        () => {
          const root = document.querySelector('#market-mate-offer-list-toolbar')?.shadowRoot;
          if (!root) return ['NO_HOST'];
          return Array.from(root.querySelectorAll('label')).map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim()).slice(0, 5);
        }
        ''')
        logs.append(f'LABELS_AFTER_SELECT={labels_after_select}')

        page.mouse.move(bx - 30, by)
        page.wait_for_timeout(120)
        page.mouse.move(bx, by, steps=12)
        page.wait_for_timeout(120)
        page.mouse.down()
        page.wait_for_timeout(90)
        page.mouse.up()
        page.wait_for_timeout(1000)

        found = None
        deadline = time.time() + 35
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
            logs.append('FOUND=None')
            logs.append(f'LATEST_NOW={latest}')
            if latest:
                logs.append(f'LATEST_MTIME={latest.stat().st_mtime}')
                logs.append(f'LATEST_SIZE={latest.stat().st_size}')

        popup_probe = page.evaluate(r'''
        () => {
          const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const host = document.querySelector('#market-mate-offer-list-toolbar');
          const root = host?.shadowRoot;
          const shadowTexts = root ? Array.from(root.querySelectorAll('*')).map((el) => normalize(el.textContent || '')).filter(Boolean).filter((t) => t.includes('导出') || t.includes('确认') || t.includes('确定') || t.includes('取消') || t.includes('设置') || t.includes('主图链接') || t.includes('商品链接') || t.includes('所在地') || t.includes('上架时间')).slice(0, 80) : [];
          const docTexts = Array.from(document.querySelectorAll('*')).map((el) => normalize(el.textContent || '')).filter(Boolean).filter((t) => t.includes('导出') || t.includes('确认') || t.includes('确定') || t.includes('取消') || t.includes('设置') || t.includes('主图链接') || t.includes('商品链接') || t.includes('所在地') || t.includes('上架时间')).slice(0, 80);
          return {shadowTexts, docTexts};
        }
        ''')
        logs.append(f'POPUP={popup_probe}')

    STATE.write_text('\n'.join(logs), encoding='utf-8')
    print(f'WROTE={STATE}')
    browser.close()
