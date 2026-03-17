const fs = require('fs');

const endpoint = 'http://127.0.0.1:9222';
const output = 'd:\\vscode\\1688_auto_trial\\exports\\channel_auto_beauty_50_fresh.csv';

async function main() {
  const targets = await (await fetch(endpoint + '/json/list')).json();
  const page = targets.find((t) => t.type === 'page' && String(t.url || '').includes('air.1688.com/app/channel-fe/search/index.html'));
  if (!page) throw new Error('page not found');

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', reject, { once: true });
  });

  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', (event) => {
    const message = JSON.parse(String(event.data));
    if (!message.id) return;
    const item = pending.get(message.id);
    if (!item) return;
    pending.delete(message.id);
    if (message.error) item.reject(new Error(message.error.message || JSON.stringify(message.error)));
    else item.resolve(message.result);
  });

  const send = (method, params = {}) => new Promise((resolve, reject) => {
    id += 1;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });

  const expression = `(() => {
    const normalize = (s) => (s || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
    const getProvinceLike = (text) => {
      const source = normalize(text);
      if (!source) return '';
      const patterns = [
        /([\\u4e00-\\u9fa5]{2,8}(?:省|市|自治区|特别行政区))/,
        /([\\u4e00-\\u9fa5]{2,8}(?:地区|盟))/,
        /([\\u4e00-\\u9fa5]{2,8}(?:县|区))/,
      ];
      for (const pattern of patterns) {
        const match = source.match(pattern);
        if (match) return match[1];
      }
      return '';
    };
    const getListedTimeText = (card) => {
      const pluginText = normalize(card.querySelector('.plugin-offer-search-card')?.textContent || '');
      const fullText = normalize(card.innerText || '');
      const source = pluginText || fullText;
      const patterns = [
        /上架日期[:：]?\\s*(\\d{4}[-/.]\\d{2}[-/.]\\d{2}(?:（[^）]*）|\\([^)]*\\))?)/,
        /上架时间[:：]?\\s*(\\d{4}[-/.]\\d{2}[-/.]\\d{2}(?:（[^）]*）|\\([^)]*\\))?)/,
        /(\\d{4}[-/.]\\d{2}[-/.]\\d{2}(?:（[^）]*）|\\([^)]*\\))?)\\s*上架/
      ];
      for (const pattern of patterns) {
        const match = source.match(pattern);
        if (match && match[1]) return normalize(match[1]);
      }
      return '';
    };
    const getAnnualSales = (card) => {
      const pluginText = normalize(card.querySelector('.plugin-offer-search-card')?.textContent || '');
      const fullText = normalize(card.innerText || '');
      const source = pluginText || fullText;
      const patterns = [
        /年销量[:：]?\\s*(.+?)(?=上架日期|上架时间|评论数|开店|$)/,
        /年销[:：]?\\s*(.+?)(?=上架日期|上架时间|评论数|开店|$)/,
        /年售[:：]?\\s*(.+?)(?=上架日期|上架时间|评论数|开店|$)/,
      ];
      for (const pattern of patterns) {
        const match = source.match(pattern);
        if (match && match[1]) {
          const value = normalize(match[1]).replace(/^量[:：]?/, '');
          if (value && value !== '-' && value !== '阅?-') return value;
        }
      }
      return '';
    };
    const sort = Array.from(document.querySelectorAll('.sort-filter-trigger')).find((el) => normalize(el.textContent) === '上架时间');
    const cards = Array.from(document.querySelectorAll('a.fx-offer-card[href*="detail.1688.com/offer/"]')).slice(0, 50);
    return {
      sortClass: sort ? String(sort.className || '') : '',
      rows: cards.map((card) => {
        const title = normalize(card.querySelector('.offer-body__title')?.textContent || card.getAttribute('title') || '');
        const supplier = normalize(card.querySelector('.shop-name')?.textContent || '');
        const image = card.querySelector('img.offer-header__image, img');
        const imageUrl = image?.currentSrc || image?.getAttribute('src') || '';
        const price = normalize(card.querySelector('.fx-offer-card-v2-price')?.textContent || '').replace(/^￥\\s*/, '');
        const deliveryInfo = normalize(card.querySelector('.fx-offer-card-v2-delivery-info')?.textContent || '');
        const pluginText = normalize(card.querySelector('.plugin-offer-search-card')?.textContent || '');
        const fullText = normalize(card.innerText || '');
        const categoryMatch = (pluginText || fullText).match(/类目[:：]?\\s*(.+?)(?=年销量|年销|年售|上架日期|上架时间|评论数|开店|$)/);
        return {
          '类目': normalize(categoryMatch?.[1] || '汽车用品 > 美容养护'),
          '商品名': title,
          '上架时间': getListedTimeText(card),
          '年销量': getAnnualSales(card),
          '商品原链接': card.href || '',
          '商品图片链接': imageUrl,
          '价格': price,
          '供货商': supplier,
          '所在地（近似）': getProvinceLike(deliveryInfo) || getProvinceLike(fullText) || getProvinceLike(supplier),
        };
      }),
    };
  })()`;

  const result = await send('Runtime.evaluate', { expression, returnByValue: true });
  const payload = result.result.value;
  if (!payload || !payload.rows || !payload.rows.length) throw new Error('no rows');

  const headers = ['类目', '商品名', '上架时间', '年销量', '商品原链接', '商品图片链接', '价格', '供货商', '所在地（近似）'];
  const esc = (value) => {
    const text = value == null ? '' : String(value);
    return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  };
  const csv = '\uFEFF' + [headers.join(',')].concat(payload.rows.map((row) => headers.map((h) => esc(row[h] || '')).join(','))).join('\r\n') + '\r\n';

  fs.writeFileSync(output, csv, 'utf8');
  fs.writeFileSync(output.replace(/\.csv$/i, '.debug.json'), JSON.stringify(payload, null, 2), 'utf8');

  console.log('SORT_CLASS=' + payload.sortClass);
  console.log('OUTPUT=' + output);
  console.log('ROW1_DATE=' + (payload.rows[0]['上架时间'] || ''));
  console.log('ROW2_DATE=' + (payload.rows[1]['上架时间'] || ''));
  console.log('ROW3_DATE=' + (payload.rows[2]['上架时间'] || ''));
  ws.close();
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
