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
FIELDNAMES = ["商品名", "上架时间", "发货地", "供应商", "价格", "90天内销量", "产品原链接"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Semi-automatic scraper for the current visible 1688 product list page."
    )
    parser.add_argument("--url", default=TARGET_URL, help="Target 1688 page URL.")
    parser.add_argument("--output", default="1688_products_page1.csv", help="Output CSV path.")
    parser.add_argument(
        "--user-data-dir",
        default=".playwright-1688-profile",
        help="Persistent browser profile directory.",
    )
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode.")
    parser.add_argument("--timeout", type=int, default=90000, help="Timeout in milliseconds.")
    return parser.parse_args()


def wait_until_ready(page, url: str, timeout: int) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    page.wait_for_load_state("networkidle", timeout=timeout)

    try:
        page.wait_for_function(
            """
            () => {
              const text = document.body?.innerText || "";
              return text.includes("开始筛选")
                || text.includes("综合排序")
                || document.querySelectorAll("a[href*='detail.1688.com/offer/']").length >= 20;
            }
            """,
            timeout=20000,
        )
    except PlaywrightTimeoutError:
        print("页面可能还没准备好，先手动登录或切到目标页。", file=sys.stderr)
        input("准备好后按 Enter 继续...")


def extract_products(page) -> tuple[list[dict[str, str]], dict[str, int]]:
    payload = page.evaluate(
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

          const inlinePricePattern = /[¥￥]\s*(\d+)(?:\.(\d{1,2}))?/;
          const salesPattern = /90天销\s*[^ ]*件/;
          const listingTimePattern = /\d{4}\/\d{2}\/\d{2}\s*上架/;
          const ignoreTitlePattern = /^(找同款|Choice|诚信通|回头率|发货地|发货时间|综合服务|旺旺响应率|工贸\/加工类型|先采后付)$/i;
          const labelSet = new Set(["回头率", "发货地", "发货时间", "综合服务", "旺旺响应率", "工贸/加工类型"]);

          const formatPrice = (integerPart, decimalPart = "") => {
            if (!decimalPart || decimalPart === "00") {
              return integerPart;
            }
            return `${integerPart}.${decimalPart}`;
          };

          const getLines = (card) =>
            card.innerText
              .split(/\n+/)
              .map((line) => normalize(line))
              .filter(Boolean);

          const parsePriceFromVisualNodes = (card) => {
            const nodes = [...card.querySelectorAll("*")]
              .filter((el) => isVisible(el))
              .map((el) => {
                const text = normalize(el.textContent);
                const rect = el.getBoundingClientRect();
                return {
                  text,
                  left: rect.left,
                  right: rect.right,
                  top: rect.top,
                  height: rect.height,
                };
              })
              .filter((item) => item.text);

            const currencyNodes = nodes.filter((item) => /[¥￥]/.test(item.text));

            for (const base of currencyNodes) {
              const rowNodes = nodes
                .filter((item) => {
                  const sameRow = Math.abs(item.top - base.top) <= Math.max(8, Math.min(base.height, 20));
                  const nearX = item.right >= base.left - 4 && item.left <= base.right + 80;
                  return sameRow && nearX;
                })
                .sort((a, b) => a.left - b.left);

              const baseIndex = rowNodes.findIndex((item) => item.left === base.left && item.top === base.top);
              if (baseIndex === -1) {
                continue;
              }

              let integerPart = "";
              let decimalPart = "";
              let sawDot = false;

              for (let i = baseIndex; i < rowNodes.length; i += 1) {
                const prev = i > baseIndex ? rowNodes[i - 1] : null;
                const current = rowNodes[i];
                const token = current.text.replace(/\s+/g, "");

                if (prev && current.left - prev.right > 14) {
                  break;
                }
                if (!token || token.includes("90天销")) {
                  break;
                }

                if (i === baseIndex) {
                  const match = token.match(/[¥￥](\d+)(?:\.(\d{1,2}))?/);
                  if (match) {
                    integerPart = match[1];
                    if (match[2]) {
                      decimalPart = match[2];
                      break;
                    }
                    continue;
                  }
                  if (/^[¥￥]$/.test(token)) {
                    continue;
                  }
                  break;
                }

                if (!integerPart && /^\d+$/.test(token)) {
                  integerPart = token;
                  continue;
                }

                if (/^\.$/.test(token)) {
                  sawDot = true;
                  continue;
                }

                if (/^\.\d{1,2}$/.test(token)) {
                  decimalPart = token.slice(1);
                  break;
                }

                if (sawDot && /^\d{1,2}$/.test(token)) {
                  decimalPart = token;
                  break;
                }

                if (integerPart && /^\d+$/.test(token)) {
                  break;
                }

                break;
              }

              if (integerPart) {
                return formatPrice(integerPart, decimalPart);
              }
            }

            return "";
          };

          const parsePriceFromLines = (lines) => {
            for (let i = 0; i < lines.length; i += 1) {
              const line = lines[i];
              const match = line.match(inlinePricePattern);
              if (match) {
                return formatPrice(match[1], match[2] || "");
              }

              if (/^[¥￥]\s*\d+$/.test(line)) {
                const nextLine = lines[i + 1] || "";
                const decimalMatch = nextLine.match(/^\.(\d{1,2})$/);
                return formatPrice(line.replace(/[¥￥]\s*/g, ""), decimalMatch ? decimalMatch[1] : "");
              }
            }
            return "";
          };

          const allOfferAnchors = [...document.querySelectorAll("a[href*='detail.1688.com/offer/']")]
            .filter((anchor) => isVisible(anchor));
          const imageAnchors = allOfferAnchors.filter((anchor) => anchor.querySelector("img"));
          const anchors = imageAnchors.length ? imageAnchors : allOfferAnchors;

          const findCard = (anchor) => {
            let node = anchor;
            for (let i = 0; i < 10 && node; i += 1) {
              const rect = node.getBoundingClientRect();
              const text = normalize(node.innerText);
              if (
                rect.width >= 180 &&
                rect.width <= 520 &&
                rect.height >= 220 &&
                rect.height <= 1500 &&
                (text.includes("发货地") || text.includes("诚信通") || /[¥￥]/.test(text))
              ) {
                return node;
              }
              node = node.parentElement;
            }
            return null;
          };

          const getListingTime = (lines) => {
            const line = lines.find((value) => listingTimePattern.test(value));
            return line || "";
          };

          const getTitle = (lines) => {
            const priceIndex = lines.findIndex((line) => /[¥￥]/.test(line));
            const upperBound = priceIndex >= 0 ? priceIndex : lines.length;

            for (let i = 0; i < upperBound; i += 1) {
              const line = lines[i];
              if (
                line.length >= 8 &&
                !listingTimePattern.test(line) &&
                !ignoreTitlePattern.test(line) &&
                !/[¥￥]/.test(line) &&
                !salesPattern.test(line)
              ) {
                return line;
              }
            }
            return "";
          };

          const getValueAfterLabel = (lines, label) => {
            const index = lines.findIndex((line) => line === label);
            if (index === -1) {
              return "";
            }

            for (let i = index + 1; i < lines.length; i += 1) {
              const line = lines[i];
              if (!line || ignoreTitlePattern.test(line)) {
                continue;
              }
              if (labelSet.has(line)) {
                break;
              }
              return line;
            }
            return "";
          };

          const getSupplier = (lines) => {
            const index = lines.findIndex((line) => line.startsWith("工贸/加工类型"));
            if (index === -1) {
              return "";
            }

            const parts = [];
            for (let i = index + 1; i < lines.length; i += 1) {
              const line = lines[i];
              if (!line) {
                continue;
              }
              if (labelSet.has(line)) {
                break;
              }
              parts.push(line);
            }
            return normalize(parts.join(" "));
          };

          anchors.sort((a, b) => {
            const ra = a.getBoundingClientRect();
            const rb = b.getBoundingClientRect();
            return ra.top - rb.top || ra.left - rb.left;
          });

          const seenCardKeys = new Set();
          const products = [];
          let priceFromVisual = 0;
          let priceFromLines = 0;

          for (const anchor of anchors) {
            const href = anchor.href || "";
            const card = findCard(anchor);
            if (!href || !card) {
              continue;
            }

            const rect = card.getBoundingClientRect();
            const cardKey = `${Math.round(rect.top / 10)}_${Math.round(rect.left / 10)}`;
            if (seenCardKeys.has(cardKey)) {
              continue;
            }

            const lines = getLines(card);
            let price = parsePriceFromVisualNodes(card);
            if (price) {
              priceFromVisual += 1;
            } else {
              price = parsePriceFromLines(lines);
              if (price) {
                priceFromLines += 1;
              }
            }

            if (!price) {
              continue;
            }

            seenCardKeys.add(cardKey);
            const text = normalize(card.innerText);
            const salesMatch = text.match(salesPattern);
            products.push({
              "商品名": getTitle(lines),
              "上架时间": getListingTime(lines),
              "发货地": getValueAfterLabel(lines, "发货地"),
              "供应商": getSupplier(lines),
              "价格": price,
              "90天内销量": salesMatch ? salesMatch[0] : "",
              "产品原链接": href,
            });
          }

          return {
            stats: {
              offerAnchors: allOfferAnchors.length,
              imageAnchors: imageAnchors.length,
              products: products.length,
              priceFromVisual: priceFromVisual,
              priceFromLines: priceFromLines,
            },
            products: products.slice(0, 30),
          };
        }
        """
    )
    return payload["products"], payload["stats"]


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
            wait_until_ready(page, args.url, args.timeout)
            print("请手动把页面停在目标商品列表页。", file=sys.stderr)
            input("准备好后按 Enter 开始抓当前页前 30 个商品...")
            page.wait_for_timeout(1500)

            products, stats = extract_products(page)
            print(
                f"调试信息: offer链接={stats['offerAnchors']}, "
                f"图片商品链接={stats['imageAnchors']}, "
                f"提取结果={stats['products']}, "
                f"视觉价格命中={stats['priceFromVisual']}, "
                f"文本价格命中={stats['priceFromLines']}",
                file=sys.stderr,
            )

            if not products:
                raise RuntimeError("没有抓到商品数据。")

            write_csv(products, output_path)
            print(f"抓取完成，共 {len(products)} 条，已保存到: {output_path}")
            return 0
        finally:
            context.close()


if __name__ == "__main__":
    raise SystemExit(main())
