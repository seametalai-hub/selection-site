1688 auto-trial scripts

Files in this folder are isolated from the working semi-automatic scripts.

Scripts:
- `scraper_auto.py`: Python + Playwright auto-filter + scrape
- `scraper_auto.js`: Node.js + Playwright auto-filter + scrape

Current auto-flow:
1. Open 1688 inventory page
2. Click `更多类目` if needed
3. Click `汽车用品`
4. Click `座垫脚垫`
5. Click `近7天上新`
6. Click `开始筛选`
7. Scrape current page top 30 products

Notes:
- This flow avoids the old 3-level hover menu.
- It still depends on the current page text and layout.
- Login state is still required.
