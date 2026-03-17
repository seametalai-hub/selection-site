import argparse
import csv
import importlib.util
import json
import math
import re
import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

TARGET_URL = (
    "https://air.1688.com/app/1688-lp/landing-page/home/"
    "inventory/products.html?bizType=cbu&customerId=cbu"
)
ROOT = Path(__file__).resolve().parent
CATEGORIES_PATH = ROOT / "categories.json"
OUTPUT_ROOT = ROOT / "outputs"
USER_DATA_DIR = ROOT / ".playwright-1688-profile"
SCRAPER_MODULE_PATH = ROOT / "1688_auto_trial" / "scraper_auto_ext.py"
SITE_FILES = ["index.html", "products.html", "styles.css", "app.js", "data.js"]

def build_user_guide() -> str:
    return (
        "选品 Product V1.0 操作说明\n\n"
        "一、版本说明\n"
        "- 当前版本名称：选品 Product V1.0\n"
        "- 当前能力：基础产品数据加载、类目浏览、搜索、排序、筛选、查看原链接\n"
        "- 数据来源：1688 选品抓取结果，已生成到 products.json\n\n"
        "二、文件说明\n"
        "请保持 demo 文件夹完整，不要只单独移动某一个文件。\n"
        "主要文件包括：\n"
        "- index.html：首页类目页\n"
        "- products.html：商品列表页\n"
        "- products.json：商品数据\n"
        "- start_preview.bat：Windows 启动脚本\n"
        "- start_preview.command：Mac 启动脚本\n\n"
        "三、Windows 使用方法\n"
        "1. 双击 start_preview.bat\n"
        "2. 会弹出一个终端窗口，请不要关闭这个终端窗口\n"
        "3. 稍等 2 到 5 秒，浏览器会自动打开网页\n"
        "4. 如果浏览器没有自动打开，请手动打开以下地址：\n"
        "http://127.0.0.1:8123/index.html\n"
        "5. 使用完成后，可以关闭终端窗口，网页本地服务也会随之停止\n\n"
        "四、Mac 使用方法\n"
        "1. 双击 start_preview.command\n"
        "2. 如果系统拦截，请右键文件，选择‘用终端打开’\n"
        "3. 终端启动后，请保持终端窗口不要关闭\n"
        "4. 如果浏览器没有自动打开，请手动打开以下地址：\n"
        "http://127.0.0.1:8123/index.html\n\n"
        "五、手动启动方式\n"
        "如果脚本无法正常运行，可手动启动本地服务。\n\n"
        "Windows：\n"
        "python -m http.server 8123\n\n"
        "Mac：\n"
        "python3 -m http.server 8123\n\n"
        "然后手动打开：\n"
        "http://127.0.0.1:8123/index.html\n\n"
        "六、网页内可做的操作\n"
        "- 首页点击类目进入商品列表\n"
        "- 搜索商品名或供应商\n"
        "- 按上架时间排序\n"
        "- 按销量排序\n"
        "- 按价格排序\n"
        "- 按发货地筛选\n"
        "- 按价格区间筛选\n"
        "- 点击‘查看原链接’跳转到 1688 商品页\n\n"
        "七、注意事项\n"
        "- 必须保持 demo 文件夹完整\n"
        "- 启动后不要关闭终端窗口，否则网页会断开\n"
        "- 当前图片使用网络图片地址，所以演示电脑需要联网\n"
        "- 第一次打开如果显示旧数据，请刷新浏览器\n"
        "- 如果浏览器打不开，请直接复制地址到浏览器：\n"
        "http://127.0.0.1:8123/index.html\n\n"
        "八、常见问题\n"
        "1. 双击后网页没打开\n"
        "处理方法：手动在浏览器输入 http://127.0.0.1:8123/index.html\n\n"
        "2. 网页打不开\n"
        "处理方法：\n"
        "- 检查终端窗口是否已关闭\n"
        "- 检查电脑是否安装 Python / Python3\n"
        "- 检查 8123 端口是否被占用\n\n"
        "3. 图片没显示\n"
        "处理方法：\n"
        "- 检查网络是否正常\n"
        "- 当前版本图片为在线图片地址，断网时可能无法显示\n\n"
        "4. Mac 提示无法验证脚本\n"
        "处理方法：\n"
        "- 右键 start_preview.command\n"
        "- 选择‘用终端打开’\n"
        "- 或手动执行 python3 -m http.server 8123\n\n"
        "九、当前版本定位\n"
        "当前版本主要用于：\n"
        "- 演示选品网页结构\n"
        "- 演示类目商品数据加载\n"
        "- 演示基础搜索、排序、筛选能力\n\n"
        "当前版本暂未覆盖：\n"
        "- 自动定时更新\n"
        "- OpenClaw 自动触发\n"
        "- 飞书自动回传\n"
        "- 增量分析和去重分析\n\n"
        "十、当前数据说明\n"
        "- 当前为 2026-03-16 全量抓取结果\n"
        "- 共 12 个类目\n"
        "- 当前总商品数：5201\n\n"
        "十一、联系人说明\n"
        "如果后续需要更新数据，请运行统一命令：\n"
        "python update_products.py run\n\n"
        "这条命令会自动完成：\n"
        "- 爬虫\n"
        "- 转 products.json\n"
        "- 生成网页\n"
        "- 发布最新数据\n"
        "- 打包演示包\n"
    )


def load_scraper_module():
    spec = importlib.util.spec_from_file_location("scraper_auto_ext", SCRAPER_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load scraper module from {SCRAPER_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified CLI workflow for 1688 selection data updates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--categories", default=str(CATEGORIES_PATH), help="Path to category config JSON.")
        subparser.add_argument("--target-date", default=datetime.now().strftime("%Y-%m-%d"), help="Output date label.")
        subparser.add_argument("--run-label", default=datetime.now().strftime("run-%H%M%S"), help="Run folder label.")
        subparser.add_argument("--output-root", default=str(OUTPUT_ROOT), help="Root output directory.")
        subparser.add_argument("--user-data-dir", default=str(USER_DATA_DIR), help="Playwright user data directory.")
        subparser.add_argument("--timeout", type=int, default=90000, help="Browser timeout in milliseconds.")
        subparser.add_argument("--headless", action="store_true", help="Run browser headlessly.")
        subparser.add_argument("--limit-categories", type=int, default=0, help="Limit the number of categories for a partial run.")

    add_common(subparsers.add_parser("run", help="Run the full workflow."))
    add_common(subparsers.add_parser("scrape", help="Scrape categories into raw CSV files."))

    generate_json = subparsers.add_parser("generate-json", help="Build products.json from raw CSV files.")
    generate_json.add_argument("--run-dir", required=True, help="Run directory containing raw CSV files.")

    build_site = subparsers.add_parser("build-site", help="Create the site folder for a run.")
    build_site.add_argument("--run-dir", required=True, help="Run directory containing products.json.")

    package_cmd = subparsers.add_parser("package", help="Create demo ZIP package for a run.")
    package_cmd.add_argument("--run-dir", required=True, help="Run directory containing the built site.")

    publish_cmd = subparsers.add_parser("publish", help="Publish a run to the root preview site.")
    publish_cmd.add_argument("--run-dir", required=True, help="Run directory containing the built site.")

    report = subparsers.add_parser("report", help="Print summary information for a run.")
    report.add_argument("--run-dir", required=True, help="Run directory to summarize.")

    estimate = subparsers.add_parser("estimate", help="Estimate full-run duration from current config.")
    estimate.add_argument("--categories", default=str(CATEGORIES_PATH), help="Path to category config JSON.")
    return parser.parse_args()


def slugify(value: str) -> str:
    return (
        value.replace("/", "_")
        .replace(" ", "")
        .replace("（", "_")
        .replace("）", "")
        .replace("(", "_")
        .replace(")", "")
    )


def load_categories(path: Path, limit: int = 0) -> list[dict[str, Any]]:
    items = json.loads(path.read_text(encoding="utf-8-sig"))
    enabled = [item for item in items if item.get("enabled", True)]
    return enabled[:limit] if limit > 0 else enabled


def prepare_run_dirs(output_root: Path, target_date: str, run_label: str) -> dict[str, Path]:
    run_dir = output_root / target_date / run_label
    raw_dir = run_dir / "raw"
    site_dir = run_dir / "site"
    package_dir = run_dir / "package"
    for directory in [run_dir, raw_dir, site_dir, package_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return {"run_dir": run_dir, "raw_dir": raw_dir, "site_dir": site_dir, "package_dir": package_dir}


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    if not rows:
        return
    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def scrape_all_categories(args: argparse.Namespace) -> Path:
    scraper = load_scraper_module()
    categories = load_categories(Path(args.categories), args.limit_categories)
    dirs = prepare_run_dirs(Path(args.output_root), args.target_date, args.run_label)
    manifest: dict[str, Any] = {
        "target_date": args.target_date,
        "run_label": args.run_label,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "categories": [],
    }

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(Path(args.user_data_dir)),
            headless=args.headless,
            viewport={"width": 1440, "height": 1100},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(args.timeout)

        try:
            scraper.wait_until_ready(page, TARGET_URL, args.timeout)
            for category in categories:
                sub_category = category["sub_category"]
                target_items = int(category.get("target_items", 500))
                pages = max(math.ceil(target_items / 30) + 2, 1)
                started = time.time()

                page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=args.timeout)
                page.wait_for_load_state("networkidle", timeout=args.timeout)
                scraper.apply_auto_filters(
                    page,
                    args.timeout,
                    main_category=category["main_category"],
                    sub_category=sub_category,
                    listing_range=category.get("listing_range", "近7天上新"),
                )
                rows, page_stats = scraper.scrape_pages(
                    page,
                    args.timeout,
                    main_category=category["main_category"],
                    sub_category=sub_category,
                    max_items=target_items,
                    pages=pages,
                )

                csv_path = dirs["raw_dir"] / f"{slugify(sub_category)}.csv"
                write_csv(rows, csv_path)
                duration_seconds = round(time.time() - started, 1)
                manifest["categories"].append(
                    {
                        "main_category": category["main_category"],
                        "sub_category": sub_category,
                        "target_items": target_items,
                        "scraped_items": len(rows),
                        "pages_requested": pages,
                        "pages_used": len(page_stats),
                        "duration_seconds": duration_seconds,
                        "csv": str(csv_path.relative_to(dirs["run_dir"])),
                        "page_stats": page_stats,
                    }
                )
                print(f"[{sub_category}] scraped {len(rows)} items in {duration_seconds}s -> {csv_path}")
        finally:
            context.close()

    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    (dirs["run_dir"] / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return dirs["run_dir"]


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: dict[str, dict[str, str]] = {}
    for row in rows:
        key = row.get("产品原链接") or f"{row.get('子类目', '')}|{row.get('商品名', '')}"
        deduped[key] = row
    return list(deduped.values())


def clean_supplier_name(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    noise_tokens = ["品质可靠退款低", "一件起订", "先采后付", "包邮", "回头率", "诚信通"]
    for token in noise_tokens:
        text = text.replace(token, " ")
    text = re.sub(r"(^|\s)-+(?=\s|$)", " ", text)
    text = re.sub(r"^[-\s]+|[-\s]+$", "", text)
    return " ".join(text.split())


def build_products_payload(rows: list[dict[str, str]], generated_at: str) -> dict[str, Any]:
    products = []
    for row in rows:
        products.append(
            {
                "category": row.get("大类目", ""),
                "subCategory": row.get("子类目", ""),
                "title": row.get("商品名", ""),
                "price": row.get("价格", ""),
                "origin": row.get("发货地", ""),
                "sales_90d": row.get("90天内销量", ""),
                "listed_time": row.get("上架时间", ""),
                "image_url": row.get("图片链接", ""),
                "product_url": row.get("产品原链接", ""),
                "sku": row.get("货号", ""),
                "supplier_name": clean_supplier_name(row.get("供应商", "")),
            }
        )
    return {"generated_at": generated_at, "total": len(products), "products": products}


def generate_json(run_dir: Path) -> Path:
    rows: list[dict[str, str]] = []
    for csv_path in sorted((run_dir / "raw").glob("*.csv")):
        rows.extend(read_csv_rows(csv_path))
    deduped = dedupe_rows(rows)
    payload = build_products_payload(deduped, run_dir.parent.name)
    output_path = run_dir / "products.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "raw_rows": len(rows),
        "deduped_rows": len(deduped),
        "categories": len({row.get('子类目', '') for row in deduped}),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_site(run_dir: Path) -> Path:
    site_dir = run_dir / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    for filename in SITE_FILES:
        shutil.copy2(ROOT / filename, site_dir / filename)
    shutil.copy2(run_dir / "products.json", site_dir / "products.json")
    return site_dir


def build_package(run_dir: Path) -> Path:
    site_dir = build_site(run_dir)
    package_dir = run_dir / "package"
    demo_dir = package_dir / "demo"
    if demo_dir.exists():
        shutil.rmtree(demo_dir)
    shutil.copytree(site_dir, demo_dir)
    shutil.copy2(ROOT / "start_preview.bat", demo_dir / "start_preview.bat")
    mac_script = ROOT / "demo" / "start_preview.command"
    if mac_script.exists():
        shutil.copy2(mac_script, demo_dir / "start_preview.command")
    guide_text = build_user_guide()
    (ROOT / "SELECTION_PRODUCT_V1_GUIDE.txt").write_text(guide_text, encoding="utf-8")
    (demo_dir / "README.txt").write_text(guide_text, encoding="utf-8")

    zip_path = package_dir / f"demo-{run_dir.parent.name}-{run_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in demo_dir.rglob("*"):
            archive.write(file_path, file_path.relative_to(package_dir))
    return zip_path


def publish_site(run_dir: Path) -> Path:
    site_dir = build_site(run_dir)
    for filename in SITE_FILES:
        shutil.copy2(site_dir / filename, ROOT / filename)
    shutil.copy2(site_dir / "products.json", ROOT / "products.json")
    return ROOT / "products.json"


def report_run(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    summary_path = run_dir / "summary.json"
    report: dict[str, Any] = {
        "run_dir": str(run_dir),
        "manifest_exists": manifest_path.exists(),
        "summary_exists": summary_path.exists(),
    }
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        durations = [item.get("duration_seconds", 0) for item in manifest.get("categories", [])]
        scraped = [item.get("scraped_items", 0) for item in manifest.get("categories", [])]
        report["category_count"] = len(manifest.get("categories", []))
        report["scraped_total"] = sum(scraped)
        report["duration_total_seconds"] = round(sum(durations), 1)
    if summary_path.exists():
        report.update(json.loads(summary_path.read_text(encoding="utf-8-sig")))
    return report


def estimate_duration(categories_path: Path) -> dict[str, Any]:
    categories = load_categories(categories_path)
    estimated_pages = sum(math.ceil(int(item.get("target_items", 500)) / 30) for item in categories)
    optimistic_minutes = round(estimated_pages * 8 / 60, 1)
    conservative_minutes = round(estimated_pages * 15 / 60, 1)
    return {
        "categories": len(categories),
        "estimated_pages": estimated_pages,
        "optimistic_minutes": optimistic_minutes,
        "conservative_minutes": conservative_minutes,
    }


def main() -> int:
    args = parse_args()

    if args.command == "estimate":
        print(json.dumps(estimate_duration(Path(args.categories)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "scrape":
        print(scrape_all_categories(args))
        return 0
    if args.command == "generate-json":
        print(generate_json(Path(args.run_dir)))
        return 0
    if args.command == "build-site":
        print(build_site(Path(args.run_dir)))
        return 0
    if args.command == "package":
        print(build_package(Path(args.run_dir)))
        return 0
    if args.command == "publish":
        print(publish_site(Path(args.run_dir)))
        return 0
    if args.command == "report":
        print(json.dumps(report_run(Path(args.run_dir)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "run":
        run_dir = scrape_all_categories(args)
        generate_json(run_dir)
        build_site(run_dir)
        publish_path = publish_site(run_dir)
        zip_path = build_package(run_dir)
        report = report_run(run_dir)
        report["published"] = str(publish_path)
        report["package"] = str(zip_path)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())










