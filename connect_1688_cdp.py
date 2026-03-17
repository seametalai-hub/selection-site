# -*- coding: utf-8 -*-
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

TARGET_URL = "https://air.1688.com/app/channel-fe/search/index.html#/result?spm=a260k.home2025.leftmenu_COLLAPSE.dfenxiaoxuanpin0of0fenxiao"
DOWNLOAD_DIR = Path(r"d:\vscode\1688_auto_trial\downloads")
STATE_PATH = Path(r"d:\vscode\1688_auto_trial\cdp_export_state.json")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Attach Playwright to a real Chrome via CDP and probe 1688 export flow.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:9222", help="Chrome CDP endpoint")
    parser.add_argument("--url", default=TARGET_URL, help="Target URL")
    parser.add_argument("--main-category", default="汽车用品")
    parser.add_argument("--sub-category", default="美容养护")
    parser.add_argument("--sort-text", default="上架时间")
    parser.add_argument("--download-dir", default=str(DOWNLOAD_DIR))
    parser.add_argument("--state-path", default=str(STATE_PATH))
    return parser.parse_args()


def ensure_page(browser, url: str):
    context = browser.contexts[0] if browser.contexts else browser.new_context(accept_downloads=True)
    page = context.pages[0] if context.pages else context.new_page()
    page.bring_to_front()
    if not page.url or "air.1688.com" not in page.url:
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_load_state("networkidle", timeout=90000)
    page.wait_for_timeout(1500)
    return context, page


def hover_main_category(page, text: str):
    page.evaluate(r"""
        ([target]) => {
          const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const trigger = Array.from(document.querySelectorAll('span'))
            .find((el) => normalize(el.textContent) === target && String(el.className).includes('category-item__trigger'));
          if (!trigger) throw new Error(`main category trigger not found: ${target}`);
          trigger.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
          trigger.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
        }
        """, [text])
    page.wait_for_timeout(800)


def click_sub_category(page, text: str):
    page.evaluate(r"""
        ([target]) => {
          const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const item = Array.from(document.querySelectorAll('li,div,span'))
            .find((el) => normalize(el.textContent) === target && String(el.className).includes('fx-cascader-menu-item'));
          if (!item) throw new Error(`sub category item not found: ${target}`);
          item.click();
        }
        """, [text])
    page.wait_for_load_state('networkidle', timeout=90000)
    page.wait_for_timeout(1800)


def click_sort(page, text: str):
    page.evaluate(r"""
        ([target]) => {
          const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const sort = Array.from(document.querySelectorAll('span,div'))
            .find((el) => normalize(el.textContent) === target && String(el.className).includes('sort-filter-trigger'));
          if (!sort) throw new Error(`sort trigger not found: ${target}`);
          sort.click();
        }
        """, [text])
    page.wait_for_load_state('networkidle', timeout=90000)
    page.wait_for_timeout(2000)


def find_export_state(page) -> dict:
    return page.evaluate(r"""
        () => {
          const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const texts = Array.from(document.querySelectorAll('div,span,button,a'))
            .map((el) => normalize(el.textContent || ''))
            .filter(Boolean);
          const exportButton = texts.find((text) => text === '导出表格') || '';
          const selectedHint = texts.find((text) => /^全选\[\d+\/\d+\]$/.test(text) || /^已选[:：]/.test(text)) || '';
          const salesHint = texts.find((text) => /^有销量\[\d+\]$/.test(text)) || '';
          return {
            exportButton,
            selectedHint,
            salesHint,
            topTexts: texts.slice(0, 120),
          };
        }
        """)


def click_export(page):
    page.evaluate(r"""
        () => {
          const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const btn = Array.from(document.querySelectorAll('div,span,button,a'))
            .find((el) => normalize(el.textContent) === '导出表格');
          if (!btn) throw new Error('export button not found');
          btn.click();
        }
        """)
    page.wait_for_timeout(1200)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.download_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state_path)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.endpoint)
        _, page = ensure_page(browser, args.url)
        page.set_default_timeout(30000)

        hover_main_category(page, args.main_category)
        click_sub_category(page, args.sub_category)
        click_sort(page, args.sort_text)

        offer_count = page.locator("a[href*='detail.1688.com/offer/']").count()
        state = find_export_state(page)
        payload = {
            "offers": offer_count,
            "export_state": state,
        }
        state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OFFERS={offer_count}")
        print(f"EXPORT_BUTTON={'YES' if state.get('exportButton') else 'NO'}")
        print(f"STATE_PATH={state_path}")

        if state.get("exportButton"):
            try:
                with page.expect_download(timeout=15000) as dl_info:
                    click_export(page)
                download = dl_info.value
                target = out_dir / download.suggested_filename
                download.save_as(str(target))
                print(f"DOWNLOADED={target}")
            except Exception as exc:
                print(f"DOWNLOAD_FAILED={type(exc).__name__}: {exc}")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

