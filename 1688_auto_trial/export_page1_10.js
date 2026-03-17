const fs = require('fs');

const endpoint = 'http://127.0.0.1:9222';
const output = 'd:\\vscode\\1688_auto_trial\\exports\\channel_auto_beauty_500_page1_10.csv';
const maxPages = 10;
const maxItems = 500;

async function connect() {
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
  return { ws, send };
}

function csvEscape(value) {
  const text = value == null ? '' : String(value);
  return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
}

async function main() {
  const { ws, send } = await connect();
  try {
    const waitReadyExpression = `(async () => {
      const normalize = (s) => (s || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
      const collect = () => {
        const cards = Array.from(document.querySelectorAll('a.fx-offer-card[href*="detail.1688.com/offer/"]')).slice(0, 50);
        const rows = cards.map((card) => {
          const pluginText = normalize(card.querySelector('.plugin-offer-search-card')?.textContent || '');
          const fullText = normalize(card.innerText || '');
          return {
            plugin: !!pluginText,
            listed: pluginText.includes('上架日期') || fullText.includes('上架日期'),
            sales: pluginText.includes('年销量') || fullText.includes('年销量'),
          };
        });
        return {
          pageCurrent: normalize(document.querySelector('.ant-pagination-item-active')?.textContent || '1'),
          total: rows.length,
          pluginCount: rows.filter((r) => r.plugin).length,
          listedCount: rows.filter((r) => r.listed).length,
          salesCount: rows.filter((r) => r.sales).length,
        };
      };
      let snapshot = collect();
      const started = Date.now();
      while (Date.now() - started < 5000) {
        snapshot = collect();
        if (snapshot.total >= 50 && snapshot.pluginCount >= 45 && snapshot.listedCount >= 45 && snapshot.salesCount >= 45) {
          return { ok: true, snapshot };
        }
        await new Promise((r) => setTimeout(r, 500));
      }
      return { ok: false, snapshot };
    })()`;

    const extractExpression = `(() => {
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
            if (value && value !== '-' && value !== '阅?-' && value !== '量:-') return value;
          }
        }
        return '';
      };
      const sort = Array.from(document.querySelectorAll('.sort-filter-trigger')).find((el) => normalize(el.textContent) === '上架时间');
      const cards = Array.from(document.querySelectorAll('a.fx-offer-card[href*="detail.1688.com/offer/"]')).slice(0, 50);
      const pageCurrent = normalize(document.querySelector('.ant-pagination-item-active')?.textContent || '1');
      return {
        sortClass: sort ? String(sort.className || '') : '',
        pageCurrent,
        firstHref: cards[0]?.href || '',
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
            '页码': pageCurrent,
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

    const rows = [];
    const seen = new Set();
    const pageStats = [];

    for (let pageIndex = 1; pageIndex <= maxPages && rows.length < maxItems; pageIndex += 1) {
      const readyRes = await send('Runtime.evaluate', { expression: waitReadyExpression, awaitPromise: true, returnByValue: true });
      const ready = readyRes.result.value;
      if (!ready?.ok) {
        throw new Error(`plugin fields not ready on loop ${pageIndex}: ${JSON.stringify(ready?.snapshot || {})}`);
      }

      const result = await send('Runtime.evaluate', { expression: extractExpression, returnByValue: true });
      const payload = result.result.value;
      if (!payload?.rows?.length) {
        throw new Error(`no rows on loop ${pageIndex}`);
      }
      if (!String(payload.sortClass || '').includes('actived')) {
        throw new Error(`sort not active on page ${payload.pageCurrent}: ${payload.sortClass || '<empty>'}`);
      }

      let added = 0;
      let listedNonEmpty = 0;
      let salesNonEmpty = 0;
      let categorySpecific = 0;
      for (const row of payload.rows) {
        if (row['上架时间']) listedNonEmpty += 1;
        if (row['年销量']) salesNonEmpty += 1;
        if (String(row['类目'] || '').includes(' > ')) categorySpecific += 1;
        const key = row['商品原链接'];
        if (!key || seen.has(key)) continue;
        seen.add(key);
        rows.push(row);
        added += 1;
        if (rows.length >= maxItems) break;
      }
      pageStats.push({
        page: payload.pageCurrent,
        added,
        firstHref: payload.firstHref,
        firstDate: payload.rows[0]['上架时间'] || '',
        listedNonEmpty,
        salesNonEmpty,
        categorySpecific,
        readySnapshot: ready.snapshot,
      });
      console.log(`PAGE=${payload.pageCurrent} ADDED=${added} DATE_FIELDS=${listedNonEmpty}/50 SALES_FIELDS=${salesNonEmpty}/50 CAT_FIELDS=${categorySpecific}/50 FIRST_DATE=${payload.rows[0]['上架时间'] || ''}`);

      if (pageIndex >= maxPages || rows.length >= maxItems) break;

      const nextExpression = `((prevHref) => new Promise((resolve) => {
        const normalize = (s) => (s || '').replace(/\\s+/g, ' ').trim();
        const nextBtn = document.querySelector('li[title="下一页"] button, li[title="下一页"]');
        if (!nextBtn) {
          resolve({ ok: false, reason: 'next button not found' });
          return;
        }
        nextBtn.click();
        const started = Date.now();
        const timer = setInterval(() => {
          const firstHref = document.querySelector('a.fx-offer-card[href*="detail.1688.com/offer/"]')?.href || '';
          const current = normalize(document.querySelector('.ant-pagination-item-active')?.textContent || '');
          if (firstHref && firstHref !== prevHref) { clearInterval(timer); setTimeout(() => resolve({ ok: true, firstHref, current }), 5000); return; }
          if (Date.now() - started > 15000) {
            clearInterval(timer);
            resolve({ ok: false, reason: 'timeout', firstHref, current });
          }
        }, 300);
      }))(${JSON.stringify(payload.firstHref)})`;
      const nextResult = await send('Runtime.evaluate', { expression: nextExpression, awaitPromise: true, returnByValue: true });
      const nextPayload = nextResult.result.value;
      if (!nextPayload?.ok) {
        throw new Error(`next page failed after page ${payload.pageCurrent}: ${nextPayload?.reason || 'unknown'}`);
      }
    }

    const headers = ['页码', '类目', '商品名', '上架时间', '年销量', '商品原链接', '商品图片链接', '价格', '供货商', '所在地（近似）'];
    const csv = '\uFEFF' + [headers.join(',')].concat(rows.map((row) => headers.map((h) => csvEscape(row[h] || '')).join(','))).join('\r\n') + '\r\n';
    fs.writeFileSync(output, csv, 'utf8');
    fs.writeFileSync(output.replace(/\.csv$/i, '.debug.json'), JSON.stringify({ total: rows.length, pageStats, rows }, null, 2), 'utf8');
    console.log('OUTPUT=' + output);
    console.log('TOTAL=' + rows.length);
  } finally {
    ws.close();
  }
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});


