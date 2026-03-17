import argparse
import csv
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


TARGET_URL = (
    "https://air.1688.com/app/1688-lp/landing-page/home/"
    "inventory/products.html?bizType=cbu&customerId=cbu"
)
FIELDNAMES = ["商品名", "价格", "90天内销量", "产品原链接"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape the first 30 products from the current 1688 Air product list page."
    )
    parser.add_argument("--url", default=TARGET_URL, help="Target 1688 page URL.")
    parser.add_argument(
        "--output",
        default="1688_products_page1.csv",
        help="Output CSV file path.",
    )
    parser.add_argument(
        "--user-data-dir",
        default=".playwright-1688-profile",
        help="Persistent browser profile directory.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90000,
        help="Page timeout in milliseconds.",
    )
    return parser.parse_args()


def wait_for_page_ready(page, url: str, timeout: int) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    page.wait_for_load_state("networkidle", timeout=timeout)

    try:
        page.wait_for_function(
            """
            () => {
              const text = document.body?.innerText || "";
              return text.includes("商品分类")
                || text.includes("开始筛选")
                || text.includes("90天销")
                || document.querySelectorAll("img").length > 20;
            }
            """,
            timeout=20000,
        )
    except PlaywrightTimeoutError:
        print("页面还没有进入商品列表，可能需要先手动登录。", file=sys.stderr)
        input("完成登录并打开目标列表页后，按 Enter 继续...")
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        page.wait_for_load_state("networkidle", timeout=timeout)

    page.wait_for_timeout(2000)


def extract_products(page) -> list[dict[str, str]]:
    products = page.evaluate(
        r"""
        () => {
          const normalize = (text) =>
            (text || "")
              .replace(/\u00a0/g, " ")
              .replace(/\s+/g, " ")
              .trim();

          const isVisible = (el) => {
            if (!el) {
              return false;
            }
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== "none"
              && style.visibility !== "hidden"
              && rect.width > 0
              && rect.height > 0;
          };

          const pricePattern = /[¥￥]\s*(\d+(?:\.\d{1,2})?)/;
          const salesPattern = /90天销\s*[0-9]+(?:\+)?件?/;
          const ignoreLinePattern = /上架$|^choice$|发货|回头率|综合服务|旺旺响应率|诚信通|工贸\/加工类型|先采后付/i;

          const findCard = (anchor) => {
            let node = anchor;
            for (let i = 0; i < 8 && node; i += 1) {
              const rect = node.getBoundingClientRect();
              const text = normalize(node.innerText);
              if (
                rect.width >= 180 &&
                rect.width <= 520 &&
                rect.height >= 280 &&
                rect.height <= 1400 &&
                pricePattern.test(text)
              ) {
                return node;
              }
              node = node.parentElement;
            }
            return null;
          };

          const getTitle = (card) => {
            const lines = card.innerText
              .split(/\n+/)
              .map((line) => normalize(line))
              .filter(Boolean);

            const priceIndex = lines.findIndex((line) => pricePattern.test(line));
            let title = "";

            if (priceIndex > 0) {
              for (let i = priceIndex - 1; i >= 0; i -= 1) {
                const line = lines[i];
                if (!ignoreLinePattern.test(line) && line.length >= 6) {
                  title = line;
                  break;
                }
              }
            }

            if (!title && priceIndex >= 0) {
              title = lines[priceIndex];
            }

            return normalize(
              title
                .replace(pricePattern, "")
                .replace(salesPattern, "")
            );
          };

          const imageAnchors = [...document.querySelectorAll("a[href*='detail.1688.com/offer/']")]
            .filter((anchor) => isVisible(anchor) && anchor.querySelector("img"));

          imageAnchors.sort((a, b) => {
            const ra = a.getBoundingClientRect();
            const rb = b.getBoundingClientRect();
            return ra.top - rb.top || ra.left - rb.left;
          });

          const results = [];
          const seenCards = new Set();

          for (const anchor of imageAnchors) {
            const card = findCard(anchor);
            if (!card || seenCards.has(card)) {
              continue;
            }

            const href = anchor.href || "";
            const cardText = normalize(card.innerText);
            const priceMatch = cardText.match(pricePattern);
            const title = getTitle(card);

            if (!href || !priceMatch || !title) {
              continue;
            }

            seenCards.add(card);
            const salesMatch = cardText.match(salesPattern);
            results.push({
              title,
              price: Number(priceMatch[1]).toFixed(2),
              sales_90d: salesMatch ? salesMatch[0] : "",
              product_url: href,
            });
          }

          return results.slice(0, 30);
        }
        """
    )

    return [
        {
            "商品名": item["title"],
            "价格": item["price"],
            "90天内销量": item["sales_90d"],
            "产品原链接": item["product_url"],
        }
        for item in products
    ]


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    output_path = Path(args.output).resolve()
    user_data_dir = Path(args.user_data_dir).resolve()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=args.headless,
            viewport={"width": 1440, "height": 1100},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(args.timeout)

        try:
            wait_for_page_ready(page, args.url, args.timeout)
            print("请在浏览器里手动完成筛选，并停留在目标商品列表页。", file=sys.stderr)
            input("准备好后按 Enter 开始抓取当前页前 30 个商品...")
            page.wait_for_load_state("networkidle", timeout=args.timeout)
            page.wait_for_timeout(2000)

            products = extract_products(page)
            if not products:
                raise RuntimeError("没有抓到商品数据，请确认当前页已经加载出商品卡片。")

            write_csv(products, output_path)
            print(f"抓取完成，共 {len(products)} 条，已保存到: {output_path}")
            return 0
        finally:
            context.close()


if __name__ == "__main__":
    raise SystemExit(main())
