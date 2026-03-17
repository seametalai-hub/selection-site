# -*- coding: utf-8 -*-
import csv
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT = Path(r'd:\vscode\1688_auto_trial\current_page_50.csv')
FIELDNAMES = [
    '类目',
    '商品名',
    '上架时间',
    '年销量',
    '商品原链接',
    '商品图片链接',
    '价格',
    '供货商',
    '所在地（近似）',
]

LOCATION_HINTS = [
    '北京', '上海', '天津', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江', '江苏', '浙江', '安徽', '福建', '江西', '山东',
    '河南', '湖北', '湖南', '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾', '内蒙古', '广西', '西藏',
    '宁夏', '新疆', '香港', '澳门', '深圳', '广州', '东莞', '佛山', '中山', '珠海', '汕头', '义乌', '金华', '杭州', '宁波', '温州',
    '台州', '绍兴', '嘉兴', '湖州', '苏州', '无锡', '常州', '南通', '青岛', '临沂', '济南', '郑州', '泉州', '厦门', '莆田', '石家庄',
    '保定', '廊坊', '邢台', '邯郸', '义乌市', '深圳市', '广州市', '东莞市', '佛山市', '中山市', '珠海市', '金华市', '杭州市', '宁波市',
]


def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def extract_location(supplier: str) -> str:
    supplier = normalize(supplier)
    match = re.search(r'[（(]([^()（）]{2,12})[)）]', supplier)
    if match:
        inner = match.group(1)
        for hint in LOCATION_HINTS:
            if hint in inner:
                return inner
    for hint in LOCATION_HINTS:
        if hint in supplier:
            return hint
    return ''


with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]
    page = context.pages[0]
    page.bring_to_front()
    page.wait_for_timeout(1000)

    rows = page.evaluate(r'''
    () => {
      const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const cards = Array.from(document.querySelectorAll("a.fx-offer-card[href*='detail.1688.com/offer/']")).slice(0, 50);
      return cards.map((card) => {
        const title = normalize(card.querySelector('.offer-body__title')?.textContent || '');
        const supplier = normalize(card.querySelector('.shop-name')?.textContent || '');
        const image = card.querySelector('img.offer-header__image');
        const imageUrl = image?.currentSrc || image?.getAttribute('src') || '';
        const priceRoot = card.querySelector('.fx-offer-card-v2-price');
        const price = normalize(priceRoot?.textContent || '').replace(/^￥/, '');
        const plugin = normalize(card.querySelector('.plugin-offer-search-card')?.textContent || '');
        const categoryMatch = plugin.match(/类目:([^年]+?)年销量:/);
        const listedMatch = plugin.match(/上架日期:([^评开]+?)(?:评论数|开店:|$)/);
        const salesMatch = plugin.match(/年销量:([^上]+?)上架日期:/);
        return {
          '类目': categoryMatch ? normalize(categoryMatch[1]) : '',
          '商品名': title,
          '上架时间': listedMatch ? normalize(listedMatch[1]) : '',
          '年销量': salesMatch ? normalize(salesMatch[1]) : '',
          '商品原链接': card.href || '',
          '商品图片链接': imageUrl,
          '价格': price,
          '供货商': supplier,
        };
      });
    }
    ''')
    browser.close()

processed = []
for row in rows:
    processed.append({
        '类目': row.get('类目', ''),
        '商品名': row.get('商品名', ''),
        '上架时间': row.get('上架时间', ''),
        '年销量': row.get('年销量', ''),
        '商品原链接': row.get('商品原链接', ''),
        '商品图片链接': row.get('商品图片链接', ''),
        '价格': row.get('价格', ''),
        '供货商': row.get('供货商', ''),
        '所在地（近似）': extract_location(row.get('供货商', '')),
    })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(processed)

print(f'WROTE={OUTPUT}')
print(f'ROWS={len(processed)}')
