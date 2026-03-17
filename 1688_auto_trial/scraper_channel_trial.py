import argparse
import csv
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

TARGET_URL = "https://air.1688.com/app/channel-fe/search/index.html#/result?spm=a260k.home2025.leftmenu_COLLAPSE.dfenxiaoxuanpin0of0fenxiao"
FIELDNAMES = [
    "大类目",
    "子类目",
    "图片链接",
    "商品名",
    "上架时间",
    "发货地",
    "供应商",
    "价格",
    "90天内销量",
    "产品原链接",
    "发货信息",
    "月代发",
    "近7天代发",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trial scraper for the new 1688 low-price source page.")
    parser.add_argument("--url", default=TARGET_URL)
    parser.add_argument("--output", default="1688_auto_trial/channel_audio_nav_50.csv")
    parser.add_argument("--user-data-dir", default="d:/vscode/.playwright-1688-profile")
    parser.add_argument("--main-category", default="汽车用品")
    parser.add_argument("--sub-category", default="影音导航")
    parser.add_argument("--sort-text", default="上架时间")
    parser.add_argument("--max-items", type=int, default=50)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=90000)
    parser.add_argument("--headless", action="store_true")
    return parser.parse_args()


def wait_until_ready(page: Page, url: str, timeout: int) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    page.wait_for_load_state("networkidle", timeout=timeout)
    page.wait_for_function(
        """
        () => {
          const offers = document.querySelectorAll("a[href*='detail.1688.com/offer/']").length;
          const body = document.body?.innerText || "";
          return offers >= 20 || body.includes("所属类目") || body.includes("综合排序");
        }
        """,
        timeout=30000,
    )
    page.wait_for_timeout(1500)


def hover_main_category(page: Page, text: str, timeout: int) -> None:
    page.evaluate(
        """
        ([target]) => {
          const normalize = (s) => (s || "").replace(/\s+/g, " ").trim();
          const trigger = Array.from(document.querySelectorAll("span"))
            .find((el) => normalize(el.textContent) === target && String(el.className).includes("category-item__trigger"));
          if (!trigger) {
            throw new Error(`main category trigger not found: ${target}`);
          }
          trigger.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
          trigger.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
        }
        """,
        [text],
    )
    page.wait_for_timeout(800)


def click_sub_category(page: Page, text: str) -> None:
    page.evaluate(
        """
        ([target]) => {
          const normalize = (s) => (s || "").replace(/\s+/g, " ").trim();
          const item = Array.from(document.querySelectorAll("li,div,span"))
            .find((el) => normalize(el.textContent) === target && String(el.className).includes("fx-cascader-menu-item"));
          if (!item) {
            throw new Error(`sub category item not found: ${target}`);
          }
          item.click();
        }
        """,
        [text],
    )
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1800)



def click_sort(page: Page, text: str) -> None:
    page.evaluate(
        """
        ([target]) => {
          const normalize = (s) => (s || "").replace(/\s+/g, " ").trim();
          const sort = Array.from(document.querySelectorAll("span,div"))
            .find((el) => normalize(el.textContent) === target && String(el.className).includes("sort-filter-trigger"));
          if (!sort) {
            throw new Error(`sort trigger not found: ${target}`);
          }
          sort.click();
        }
        """,
        [text],
    )
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)


def apply_filters(page: Page, timeout: int, *, main_category: str, sub_category: str, sort_text: str) -> None:
    page.set_default_timeout(timeout)
    hover_main_category(page, main_category, timeout)
    click_sub_category(page, sub_category)
    click_sort(page, sort_text)


def extract_products(page: Page) -> list[dict[str, str]]:
    return page.evaluate(
        """
        () => {
          const normalize = (text) => (text || "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
          const cards = Array.from(document.querySelectorAll("a.fx-offer-card[href*='detail.1688.com/offer/']"));
          const products = [];
          for (const card of cards) {
            const title = normalize(card.querySelector(".offer-body__title")?.textContent || "");
            const supplier = normalize(card.querySelector(".shop-name")?.textContent || "");
            const image = card.querySelector("img.offer-header__image");
            const imageUrl = image?.currentSrc || image?.getAttribute("src") || "";
            const priceRoot = card.querySelector(".fx-offer-card-v2-price");
            const price = normalize(priceRoot?.textContent || "").replace(/^￥/, "");
            const deliveryInfo = normalize(card.querySelector(".fx-offer-card-v2-delivery-info")?.textContent || "");
            const paragraphs = Array.from(card.querySelectorAll("p.offer-body__count"))
              .map((el) => normalize(el.textContent || ""))
              .filter(Boolean);
            const monthSales = paragraphs.find((line) => line.startsWith("月代发")) || "";
            const sales7d = paragraphs.find((line) => line.startsWith("近7天代发")) || "";
            products.push({
              "图片链接": imageUrl,
              "商品名": title,
              "上架时间": "",
              "发货地": "",
              "供应商": supplier,
              "价格": price,
              "90天内销量": "",
              "产品原链接": card.href || "",
              "发货信息": deliveryInfo,
              "月代发": monthSales,
              "近7天代发": sales7d,
            });
          }
          return products;
        }
        """
    )


def go_to_next_page(page: Page, timeout: int) -> bool:
    try:
        page.locator("li[title='下一页'] button").first.click(timeout=timeout)
        page.wait_for_load_state("networkidle", timeout=timeout)
        page.wait_for_timeout(2000)
        return True
    except PlaywrightTimeoutError:
        return False


def normalize_rows(products: list[dict[str, str]], *, main_category: str, sub_category: str) -> list[dict[str, str]]:
    rows = []
    for product in products:
        rows.append(
            {
                "大类目": main_category,
                "子类目": sub_category,
                "图片链接": product.get("图片链接", ""),
                "商品名": product.get("商品名", ""),
                "上架时间": product.get("上架时间", ""),
                "发货地": product.get("发货地", ""),
                "供应商": product.get("供应商", ""),
                "价格": product.get("价格", ""),
                "90天内销量": product.get("90天内销量", ""),
                "产品原链接": product.get("产品原链接", ""),
                "发货信息": product.get("发货信息", ""),
                "月代发": product.get("月代发", ""),
                "近7天代发": product.get("近7天代发", ""),
            }
        )
    return rows


def scrape_pages(page: Page, timeout: int, *, main_category: str, sub_category: str, max_items: int, pages: int) -> list[dict[str, str]]:
    rows = []
    seen = set()
    for page_index in range(1, pages + 1):
        products = extract_products(page)
        normalized = normalize_rows(products, main_category=main_category, sub_category=sub_category)
        added = 0
        for row in normalized:
            url = row["产品原链接"]
            if not url or url in seen:
                continue
            seen.add(url)
            rows.append(row)
            added += 1
            if len(rows) >= max_items:
                return rows
        print(f"page {page_index}: offers={len(products)} added={added} total={len(rows)}")
        if page_index >= pages:
            break
        if not go_to_next_page(page, timeout):
            break
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(Path(args.user_data_dir)),
            headless=args.headless,
            viewport={"width": 1600, "height": 1200},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(args.timeout)
        try:
            wait_until_ready(page, args.url, args.timeout)
            apply_filters(page, args.timeout, main_category=args.main_category, sub_category=args.sub_category, sort_text=args.sort_text)
            rows = scrape_pages(page, args.timeout, main_category=args.main_category, sub_category=args.sub_category, max_items=args.max_items, pages=args.pages)
            write_csv(rows, output_path)
            print(f"wrote {len(rows)} rows -> {output_path}")
        finally:
            context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
