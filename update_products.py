import argparse
import csv
import json
import shutil
import subprocess
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

TARGET_URL = "https://air.1688.com/app/channel-fe/search/index.html#/result?spm=a260k.home2025.leftmenu_COLLAPSE.dfenxiaoxuanpin0of0fenxiao"
ROOT = Path(__file__).resolve().parent
CATEGORIES_PATH = ROOT / "categories.json"
OUTPUT_ROOT = ROOT / "outputs"
SCRAPER_SCRIPT_PATH = ROOT / "1688_auto_trial" / "scraper_channel_cdp.js"
SITE_FILES = ["index.html", "products.html", "styles.css", "app.js"]
DATA_FILE = "data.js"
DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:9222"


def build_user_guide() -> str:
    return (
        "选品 Product V2.0 操作说明\n\n"
        "一、版本说明\n"
        "- 当前版本名称：选品 Product V2.0\n"
        "- 当前能力：频道页新源抓取、商品搜索、类目浏览、排序、筛选、查看原链接\n"
        "- 数据来源：1688 找低价货源频道页，已生成到 products.json\n\n"
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
        "五、统一更新命令\n"
        "python update_products.py run\n\n"
        "这条命令会自动完成：\n"
        "- 爬取 12 个类目（默认每类 500 条）\n"
        "- 生成 raw CSV\n"
        "- 合并 products.json\n"
        "- 生成网页站点文件\n"
        "- 发布本地预览数据\n"
        "- 打包演示包\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified CLI workflow for 1688 channel-page updates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--categories", default=str(CATEGORIES_PATH), help="Path to category config JSON.")
        subparser.add_argument("--target-date", default=datetime.now().strftime("%Y-%m-%d"), help="Output date label.")
        subparser.add_argument("--run-label", default=datetime.now().strftime("run-%H%M%S"), help="Run folder label.")
        subparser.add_argument("--output-root", default=str(OUTPUT_ROOT), help="Root output directory.")
        subparser.add_argument("--endpoint", default=DEFAULT_CDP_ENDPOINT, help="Chrome CDP endpoint.")
        subparser.add_argument("--wait-ms", type=int, default=5000, help="Wait time after each page switch.")
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


def run_channel_scraper(
    *,
    endpoint: str,
    output_path: Path,
    main_category: str,
    sub_category: str,
    max_items: int,
    wait_ms: int,
) -> dict[str, Any]:
    pages = max((max_items + 49) // 50, 1)
    command = [
        "node",
        str(SCRAPER_SCRIPT_PATH),
        "--endpoint",
        endpoint,
        "--output",
        str(output_path),
        "--main-category",
        main_category,
        "--sub-category",
        sub_category,
        "--max-items",
        str(max_items),
        "--pages",
        str(pages),
        "--wait-ms",
        str(wait_ms),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(
            f"channel scraper failed for {sub_category}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if result.stderr.strip():
        print(result.stderr.strip())
    return json.loads(result.stdout)


def scrape_all_categories(args: argparse.Namespace) -> Path:
    categories = load_categories(Path(args.categories), args.limit_categories)
    dirs = prepare_run_dirs(Path(args.output_root), args.target_date, args.run_label)
    manifest: dict[str, Any] = {
        "target_date": args.target_date,
        "run_label": args.run_label,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "source": "1688-channel-page",
        "categories": [],
    }

    for category in categories:
        sub_category = category["sub_category"]
        target_items = int(category.get("target_items", 500))
        csv_path = dirs["raw_dir"] / f"{slugify(sub_category)}.csv"
        started = time.time()
        payload = run_channel_scraper(
            endpoint=args.endpoint,
            output_path=csv_path,
            main_category=category["main_category"],
            sub_category=sub_category,
            max_items=target_items,
            wait_ms=args.wait_ms,
        )
        duration_seconds = round(time.time() - started, 1)
        page_stats = payload.get("pageStats", [])
        manifest["categories"].append(
            {
                "main_category": category["main_category"],
                "sub_category": sub_category,
                "target_items": target_items,
                "scraped_items": int(payload.get("total", 0)),
                "pages_requested": max((target_items + 49) // 50, 1),
                "pages_used": len(page_stats),
                "duration_seconds": duration_seconds,
                "csv": str(csv_path.relative_to(dirs["run_dir"])),
                "debug": str(Path(payload.get("debug", csv_path.with_suffix(".debug.json"))).relative_to(dirs["run_dir"])),
                "page_stats": page_stats,
            }
        )
        print(f"[{sub_category}] scraped {payload.get('total', 0)} items in {duration_seconds}s -> {csv_path}")

    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    (dirs["run_dir"] / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return dirs["run_dir"]


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: dict[str, dict[str, str]] = {}
    for row in rows:
        key = row.get("商品原链接") or row.get("产品原链接") or f"{row.get('类目', '')}|{row.get('商品名', '')}"
        deduped[key] = row
    return list(deduped.values())


def clean_supplier_name(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    noise_tokens = ["品质可靠退款低", "一件起订", "先采后付", "包邮", "回头率", "诚信通"]
    for token in noise_tokens:
        text = text.replace(token, " ")
    return " ".join(text.replace("-", " ").split())


def split_category_path(value: str) -> tuple[str, str]:
    parts = [part.strip() for part in str(value or "").split(">") if part.strip()]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], " > ".join(parts[1:])


def build_products_payload(rows: list[dict[str, str]], generated_at: str) -> dict[str, Any]:
    products = []
    for row in rows:
        if "类目" in row:
            category, sub_category = split_category_path(row.get("类目", ""))
            price = row.get("价格", "")
            origin = row.get("所在地（近似）", "")
            sales = row.get("年销量", "")
            listed_time = row.get("上架时间", "")
            image_url = row.get("商品图片链接", "")
            product_url = row.get("商品原链接", "")
            supplier = row.get("供货商", "")
            title = row.get("商品名", "")
        else:
            category = row.get("大类目", "")
            sub_category = row.get("子类目", "")
            price = row.get("价格", "")
            origin = row.get("发货地", "")
            sales = row.get("90天内销量", "")
            listed_time = row.get("上架时间", "")
            image_url = row.get("图片链接", "")
            product_url = row.get("产品原链接", "")
            supplier = row.get("供应商", "")
            title = row.get("商品名", "")

        products.append(
            {
                "category": category,
                "subCategory": sub_category,
                "title": title,
                "price": price,
                "origin": origin,
                "sales_90d": sales,
                "annual_sales": sales,
                "listed_time": listed_time,
                "image_url": image_url,
                "product_url": product_url,
                "supplier_name": clean_supplier_name(supplier),
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
        "categories": len({row.get('类目', row.get('子类目', '')) for row in deduped}),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_data_js(categories: list[dict[str, Any]]) -> str:
    payload = {
        "categories": [
            {
                "id": f"cat-{index + 1}",
                "name": item["sub_category"],
                "description": f"{item['main_category']}类目，支持跳转查看商品列表。",
            }
            for index, item in enumerate(categories)
        ],
        "dataFile": "./products.json",
    }
    return "const APP_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"


def build_site(run_dir: Path) -> Path:
    site_dir = run_dir / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    for filename in SITE_FILES:
        shutil.copy2(ROOT / filename, site_dir / filename)
    shutil.copy2(run_dir / "products.json", site_dir / "products.json")
    categories = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8-sig")).get("categories", [])
    category_payload = [
        {"main_category": item["main_category"], "sub_category": item["sub_category"]}
        for item in categories
    ]
    (site_dir / DATA_FILE).write_text(build_data_js(category_payload), encoding="utf-8")
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
    shutil.copy2(site_dir / DATA_FILE, ROOT / DATA_FILE)
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
    estimated_pages = sum(max((int(item.get("target_items", 500)) + 49) // 50, 1) for item in categories)
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
