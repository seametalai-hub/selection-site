# -*- coding: utf-8 -*-
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(r'd:\vscode\1688_auto_trial\probe_listed_time_cards.json')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)
    data = page.evaluate(r'''
    () => {
      const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const cards = Array.from(document.querySelectorAll('a.fx-offer-card[href*="detail.1688.com/offer/"]')).slice(0, 10);
      return cards.map((card, idx) => {
        const plugin = card.querySelector('.plugin-offer-search-card');
        const texts = Array.from(card.querySelectorAll('*')).map((el) => normalize(el.textContent || '')).filter(Boolean);
        const listedLine = texts.find((t) => t.includes('上架日期')) || '';
        const supplierLine = texts.find((t) => t.includes('年')) || '';
        return {
          idx,
          href: card.href || '',
          title: normalize(card.querySelector('.offer-body__title')?.textContent || ''),
          supplier: normalize(card.querySelector('.shop-name')?.textContent || ''),
          pluginText: normalize(plugin?.textContent || ''),
          listedLine,
          tailTexts: texts.slice(-20),
        };
      });
    }
    ''')
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'WROTE={OUT}')
    browser.close()
