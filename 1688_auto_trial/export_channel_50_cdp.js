const fs = require('fs');
const path = require('path');

const DEBUG_ENDPOINT = 'http://127.0.0.1:9222';
const OUTPUT_PATH = 'd:\\vscode\\1688_auto_trial\\exports\\channel_auto_beauty_50.csv';

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} for ${url}`);
  }
  return response.json();
}

async function connectToPageWs() {
  const targets = await fetchJson(`${DEBUG_ENDPOINT}/json/list`);
  const pageTarget = targets.find((target) => target.type === 'page' && String(target.url || '').includes('air.1688.com/app/channel-fe/search/index.html'));
  if (!pageTarget || !pageTarget.webSocketDebuggerUrl) {
    throw new Error('1688 channel page target not found on port 9222');
  }

  const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', reject, { once: true });
  });

  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', (event) => {
    const message = JSON.parse(String(event.data));
    if (!message.id) {
      return;
    }
    const item = pending.get(message.id);
    if (!item) {
      return;
    }
    pending.delete(message.id);
    if (message.error) {
      item.reject(new Error(message.error.message || JSON.stringify(message.error)));
      return;
    }
    item.resolve(message.result);
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
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function toCsv(rows, headers) {
  const lines = [headers.join(',')];
  for (const row of rows) {
    lines.push(headers.map((header) => csvEscape(row[header] || '')).join(','));
  }
  return `\uFEFF${lines.join('\r\n')}\r\n`;
}

async function main() {
  const { ws, send } = await connectToPageWs();

  try {
    await send('Page.enable');
    await send('Runtime.enable');

    const expression = [
      '(async () => {',
      '  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));',
      '  const normalize = (text) => (text || "").replace(/\\u00a0/g, " ").replace(/\\s+/g, " ").trim();',
      '  const args = { mainCategory: "汽车用品", subCategory: "美容养护", sortText: "上架时间", maxItems: 50 };',
      '',
      '  const isVisible = (el) => {',
      '    if (!el) return false;',
      '    const style = window.getComputedStyle(el);',
      '    const rect = el.getBoundingClientRect();',
      '    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;',
      '  };',
      '',
      '  const parseDateOnly = (text) => {',
      '    const match = normalize(text).match(/(\\d{4})[-/.](\\d{2})[-/.](\\d{2})/);',
      '    if (!match) return null;',
      '    return `${match[1]}-${match[2]}-${match[3]}`;',
      '  };',
      '',
      '  const getListedTimeText = (card) => {',
      '    const pluginText = normalize(card.querySelector(".plugin-offer-search-card")?.textContent || "");',
      '    const fullText = normalize(card.innerText || "");',
      '    const source = pluginText || fullText;',
      '    const patterns = [',
      '      /上架日期[:：]?\\s*(\\d{4}[-/.]\\d{2}[-/.]\\d{2}(?:（[^）]*）|\\([^)]*\\))?)/,',
      '      /上架时间[:：]?\\s*(\\d{4}[-/.]\\d{2}[-/.]\\d{2}(?:（[^）]*）|\\([^)]*\\))?)/,',
      '      /(\\d{4}[-/.]\\d{2}[-/.]\\d{2}(?:（[^）]*）|\\([^)]*\\))?)\\s*上架/,',
      '    ];',
      '    for (const pattern of patterns) {',
      '      const match = source.match(pattern);',
      '      if (match && match[1]) return normalize(match[1]);',
      '    }',
      '    return "";',
      '  };',
      '',
      '  const getTopDates = () => Array.from(document.querySelectorAll("a.fx-offer-card[href*=\"detail.1688.com/offer/\"]")).slice(0, 8).map((card) => parseDateOnly(getListedTimeText(card))).filter(Boolean);',
      '',
      '  const isDesc = (dates) => {',
      '    if (dates.length < 2) return false;',
      '    for (let i = 1; i < dates.length; i += 1) {',
      '      if (dates[i - 1] < dates[i]) return false;',
      '    }',
      '    return true;',
      '  };',
      '',
      '  const hoverAndSelectCategory = async () => {',
      '    window.scrollTo({ top: 0, behavior: "instant" });',
      '    await sleep(300);',
      '    const main = Array.from(document.querySelectorAll("span.category-item__trigger")).find((el) => normalize(el.textContent) === args.mainCategory && isVisible(el));',
      '    if (!main) throw new Error("main category not found");',
      '    main.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));',
      '    main.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));',
      '    await sleep(700);',
      '    const sub = Array.from(document.querySelectorAll(".fx-cascader-menu-item")).find((el) => normalize(el.textContent) === args.subCategory && isVisible(el));',
      '    if (!sub) throw new Error("sub category not found");',
      '    sub.click();',
      '    await sleep(2500);',
      '  };',
      '',
      '  const ensureSortDesc = async () => {',
      '    const sort = Array.from(document.querySelectorAll(".sort-filter-trigger")).find((el) => normalize(el.textContent) === args.sortText && isVisible(el));',
      '    if (!sort) throw new Error("sort trigger not found");',
      '    for (let attempt = 0; attempt < 3; attempt += 1) {',
      '      sort.click();',
      '      await sleep(2200);',
      '      const dates = getTopDates();',
      '      if (isDesc(dates)) return { dates, attempt: attempt + 1 };',
      '    }',
      '    return { dates: getTopDates(), attempt: 3 };',
      '  };',
      '',
      '  const getProvinceLike = (text) => {',
      '    const source = normalize(text);',
      '    if (!source) return "";',
      '    const patterns = [',
      '      /([\\u4e00-\\u9fa5]{2,8}(?:省|市|自治区|特别行政区))/,',
      '      /([\\u4e00-\\u9fa5]{2,8}(?:地区|盟))/,',
      '      /([\\u4e00-\\u9fa5]{2,8}(?:县|区))/,',
      '    ];',
      '    for (const pattern of patterns) {',
      '      const match = source.match(pattern);',
      '      if (match) return match[1];',
      '    }',
      '    return "";',
      '  };',
      '',
      '  const getAnnualSales = (card) => {',
      '    const pluginText = normalize(card.querySelector(".plugin-offer-search-card")?.textContent || "");',
      '    const fullText = normalize(card.innerText || "");',
      '    const source = pluginText || fullText;',
      '    const patterns = [',
      '      /年销量[:：]?\\s*(.+?)(?=上架日期|上架时间|评论数|开店|$)/,',
      '      /年销[:：]?\\s*(.+?)(?=上架日期|上架时间|评论数|开店|$)/,',
      '      /年售[:：]?\\s*(.+?)(?=上架日期|上架时间|评论数|开店|$)/,',
      '    ];',
      '    for (const pattern of patterns) {',
      '      const match = source.match(pattern);',
      '      if (match && match[1]) {',
      '        const value = normalize(match[1]).replace(/^量[:：]?/, "");',
      '        if (value && value !== "-") return value;',
      '      }',
      '    }',
      '    return "";',
      '  };',
      '',
      '  await hoverAndSelectCategory();',
      '  const sortState = await ensureSortDesc();',
      '',
      '  const cards = Array.from(document.querySelectorAll("a.fx-offer-card[href*=\"detail.1688.com/offer/\"]")).slice(0, args.maxItems);',
      '  const rows = [];',
      '  const debug = [];',
      '',
      '  for (const card of cards) {',
      '    const title = normalize(card.querySelector(".offer-body__title")?.textContent || card.getAttribute("title") || "");',
      '    const supplier = normalize(card.querySelector(".shop-name")?.textContent || "");',
      '    const image = card.querySelector("img.offer-header__image, img");',
      '    const imageUrl = image?.currentSrc || image?.getAttribute("src") || "";',
      '    const price = normalize(card.querySelector(".fx-offer-card-v2-price")?.textContent || "").replace(/^￥\\s*/, "");',
      '    const deliveryInfo = normalize(card.querySelector(".fx-offer-card-v2-delivery-info")?.textContent || "");',
      '    const pluginText = normalize(card.querySelector(".plugin-offer-search-card")?.textContent || "");',
      '    const fullText = normalize(card.innerText || "");',
      '    const categoryMatch = (pluginText || fullText).match(/类目[:：]?\\s*(.+?)(?=年销量|年销|年售|上架日期|上架时间|评论数|开店|$)/);',
      '    rows.push({',
      '      "类目": normalize(categoryMatch?.[1] || (args.mainCategory + " > " + args.subCategory)),',
      '      "商品名": title,',
      '      "上架时间": getListedTimeText(card),',
      '      "年销量": getAnnualSales(card),',
      '      "商品原链接": card.href || "",',
      '      "商品图片链接": imageUrl,',
      '      "价格": price,',
      '      "供货商": supplier,',
      '      "所在地（近似）": getProvinceLike(deliveryInfo) || getProvinceLike(fullText) || getProvinceLike(supplier),',
      '    });',
      '    debug.push({ title, pluginText, fullText: fullText.slice(0, 500) });',
      '  }',
      '',
      '  return {',
      '    rowCount: rows.length,',
      '    firstCategory: rows[0]?.["类目"] || "",',
      '    topDates: sortState.dates,',
      '    sortAttempts: sortState.attempt,',
      '    rows,',
      '    debug,',
      '  };',
      '})();',
    ].join('\n');

    const runtimeResult = await send('Runtime.evaluate', {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });

    const payload = runtimeResult.result?.value;
    if (!payload?.rows?.length) {
      throw new Error('No rows extracted from the current page');
    }
    if (!String(payload.firstCategory || '').includes('汽车用品 > 美容养护')) {
      throw new Error(`Unexpected first category: ${payload.firstCategory || '<empty>'}`);
    }

    fs.mkdirSync(path.dirname(OUTPUT_PATH), { recursive: true });
    const headers = ['类目', '商品名', '上架时间', '年销量', '商品原链接', '商品图片链接', '价格', '供货商', '所在地（近似）'];
    fs.writeFileSync(OUTPUT_PATH, toCsv(payload.rows, headers), 'utf8');
    fs.writeFileSync(OUTPUT_PATH.replace(/\.csv$/i, '.debug.json'), JSON.stringify(payload, null, 2), 'utf8');

    console.log(`ROWS=${payload.rowCount}`);
    console.log(`FIRST_CATEGORY=${payload.firstCategory}`);
    console.log(`TOP_DATES=${payload.topDates.join('|')}`);
    console.log(`SORT_ATTEMPTS=${payload.sortAttempts}`);
    console.log(`OUTPUT=${OUTPUT_PATH}`);
  } finally {
    ws.close();
  }
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
