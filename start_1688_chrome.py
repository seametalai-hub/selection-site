# -*- coding: utf-8 -*-
import argparse
import subprocess
import time
from pathlib import Path

TARGET_URL = "https://air.1688.com/app/channel-fe/search/index.html#/result?spm=a260k.home2025.leftmenu_COLLAPSE.dfenxiaoxuanpin0of0fenxiao"
CHROME_PATH = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
PROFILE_DIR = Path(r"d:\vscode\chrome-1688-profile")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start real Chrome for 1688 with a dedicated profile and CDP port.")
    parser.add_argument("--chrome-path", default=str(CHROME_PATH), help="Path to chrome.exe")
    parser.add_argument("--profile-dir", default=str(PROFILE_DIR), help="Dedicated Chrome profile directory")
    parser.add_argument("--port", type=int, default=9222, help="Remote debugging port")
    parser.add_argument("--url", default=TARGET_URL, help="URL to open")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chrome_path = Path(args.chrome_path)
    profile_dir = Path(args.profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    if not chrome_path.exists():
        raise FileNotFoundError(f"Chrome not found: {chrome_path}")

    cmd = [
        str(chrome_path),
        f"--user-data-dir={profile_dir}",
        "--profile-directory=Default",
        f"--remote-debugging-port={args.port}",
        "--no-first-run",
        "--no-default-browser-check",
        args.url,
    ]
    subprocess.Popen(cmd)
    time.sleep(2)
    print(f"CHROME_STARTED port={args.port}")
    print(f"PROFILE_DIR={profile_dir}")
    print("保持这个 Chrome 窗口打开。Playwright 后续会通过 CDP 接管它。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
