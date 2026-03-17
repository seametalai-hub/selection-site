# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import sync_playwright

TARGET_URL = "https://air.1688.com/app/channel-fe/search/index.html#/result?spm=a260k.home2025.leftmenu_COLLAPSE.dfenxiaoxuanpin0of0fenxiao"
USER_DATA_DIR = r"d:\vscode\.playwright-1688-profile"
DOWNLOAD_DIR = Path(r"d:\vscode\1688_auto_trial\downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def hover_main_category(page, text: str):
    page.evaluate(
        """
        ([target]) => {
          const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const trigger = Array.from(document.querySelectorAll('span'))
            .find((el) => normalize(el.textContent) === target && String(el.className).includes('category-item__trigger'));
          if (!trigger) throw new Error(`main category trigger not found: ${target}`);
          trigger.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
          trigger.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
        }
        """,
        [text],
    )
    page.wait_for_timeout(800)


def click_sub_category(page, text: str):
    page.evaluate(
        """
        ([target]) => {
          const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const item = Array.from(document.querySelectorAll('li,div,span'))
            .find((el) => normalize(el.textContent) === target && String(el.className).includes('fx-cascader-menu-item'));
          if (!item) throw new Error(`sub category item not found: ${target}`);
          item.click();
        }
        """,
        [text],
    )
    page.wait_for_load_state('networkidle', timeout=90000)
    page.wait_for_timeout(1800)


def click_sort(page, text: str):
    page.evaluate(
        """
        ([target]) => {
          const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const sort = Array.from(document.querySelectorAll('span,div'))
            .find((el) => normalize(el.textContent) === target && String(el.className).includes('sort-filter-trigger'));
          if (!sort) throw new Error(`sort trigger not found: ${target}`);
          sort.click();
        }
        """,
        [text],
    )
    page.wait_for_load_state('networkidle', timeout=90000)
    page.wait_for_timeout(2000)


def click_export(page, text: str):
    page.evaluate(
        """
        ([target]) => {
          const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
          const btn = Array.from(document.querySelectorAll('div,span,button,a'))
            .find((el) => normalize(el.textContent) === target);
          if (!btn) throw new Error(`export button not found: ${target}`);
          btn.click();
        }
        """,
        [text],
    )


with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=True,
        viewport={"width": 1600, "height": 1200},
        accept_downloads=True,
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.set_default_timeout(30000)
    page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=90000)
    page.wait_for_load_state('networkidle', timeout=90000)
    page.wait_for_timeout(2000)

    hover_main_category(page, '汽车用品')
    click_sub_category(page, '美容养护')
    click_sort(page, '上架时间')

    offers = page.locator("a[href*='detail.1688.com/offer/']").count()
    print(f"OFFERS={offers}")

    with page.expect_download(timeout=30000) as dl_info:
        click_export(page, '导出表格')
    download = dl_info.value
    target = DOWNLOAD_DIR / download.suggested_filename
    download.save_as(str(target))
    print(f"DOWNLOADED={target}")

    context.close()
