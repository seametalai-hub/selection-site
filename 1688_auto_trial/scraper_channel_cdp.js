const fs = require("fs");
const path = require("path");

const DEFAULT_ENDPOINT = "http://127.0.0.1:9222";
const DEFAULT_URL =
  "https://air.1688.com/app/channel-fe/search/index.html#/result?spm=a260k.home2025.leftmenu_COLLAPSE.dfenxiaoxuanpin0of0fenxiao";

function parseArgs(argv) {
  const args = {
    endpoint: DEFAULT_ENDPOINT,
    url: DEFAULT_URL,
    output: "d:\\vscode\\1688_auto_trial\\exports\\channel.csv",
    mainCategory: "汽车用品",
    subCategory: "美容养护",
    sortText: "上架时间",
    maxItems: 500,
    pages: 10,
    pageSize: 50,
    waitMs: 5000,
  };

  for (let i = 2; i < argv.length; i += 2) {
    const key = argv[i];
    const value = argv[i + 1];
    if (!key?.startsWith("--") || value == null) continue;
    if (key === "--endpoint") args.endpoint = value;
    if (key === "--url") args.url = value;
    if (key === "--output") args.output = value;
    if (key === "--main-category") args.mainCategory = value;
    if (key === "--sub-category") args.subCategory = value;
    if (key === "--sort-text") args.sortText = value;
    if (key === "--max-items") args.maxItems = Number(value) || args.maxItems;
    if (key === "--pages") args.pages = Number(value) || args.pages;
    if (key === "--page-size") args.pageSize = Number(value) || args.pageSize;
    if (key === "--wait-ms") args.waitMs = Number(value) || args.waitMs;
  }

  args.pages = Math.max(args.pages, Math.ceil(args.maxItems / args.pageSize));
  return args;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
  return response.json();
}

async function connectToPage(endpoint, urlFragment) {
  const targets = await fetchJson(`${endpoint}/json/list`);
  const pageTarget = targets.find(
    (target) => target.type === "page" && String(target.url || "").includes(urlFragment),
  );
  if (!pageTarget?.webSocketDebuggerUrl) {
    throw new Error(`Target page not found for ${urlFragment}`);
  }

  const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", reject, { once: true });
  });

  let id = 0;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(String(event.data));
    if (!message.id) return;
    const item = pending.get(message.id);
    if (!item) return;
    pending.delete(message.id);
    if (message.error) item.reject(new Error(message.error.message || JSON.stringify(message.error)));
    else item.resolve(message.result);
  });

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      id += 1;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });

  return { ws, send };
}

function csvEscape(value) {
  const text = value == null ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function toCsv(rows, headers) {
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(headers.map((header) => csvEscape(row[header] || "")).join(","));
  }
  return `\uFEFF${lines.join("\r\n")}\r\n`;
}
function toUnicodeEscape(value) {
  return Array.from(String(value || "")).map((char) => {
    const code = char.charCodeAt(0);
    return code > 127 ? `\\u${code.toString(16).padStart(4, "0")}` : char;
  }).join("");
}


async function main() {
  const args = parseArgs(process.argv);
  const { ws, send } = await connectToPage(args.endpoint, "air.1688.com/app/channel-fe/search/index.html");

  try {
    const state = {
      mainCategory: toUnicodeEscape(args.mainCategory),
      subCategory: toUnicodeEscape(args.subCategory),
      sortText: toUnicodeEscape(args.sortText),
      waitMs: args.waitMs,
      pageSize: args.pageSize,
    };

    const setupExpression = `((async (state) => {
      const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const normalize = (text) => (text || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
      const isVisible = (el) => {
        if (!el) return false;
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
      };
      const parseDateOnly = (text) => {
        const match = normalize(text).match(/(\\d{4})[-/.](\\d{2})[-/.](\\d{2})/);
        return match ? (match[1] + '-' + match[2] + '-' + match[3]) : '';
      };
      const extractTaggedValue = (source, labels, endLabels) => {
        const text = normalize(source);
        for (const label of labels) {
          const index = text.indexOf(label);
          if (index === -1) continue;
          let value = text.slice(index + label.length);
          let endPos = value.length;
          for (const endLabel of endLabels) {
            const endIndex = value.indexOf(endLabel);
            if (endIndex !== -1 && endIndex < endPos) endPos = endIndex;
          }
          value = normalize(value.slice(0, endPos).replace(/^[:\\uFF1A]\\s*/, ''));
          if (value) return value;
        }
        return '';
      };
      const getPluginSource = (card) => {
        const pluginText = normalize(card.querySelector('.plugin-offer-search-card')?.textContent || '');
        const fullText = normalize(card.innerText || '');
        return pluginText || fullText;
      };
      const getListedTimeText = (card) => {
        const value = extractTaggedValue(
          getPluginSource(card),
          ['\\u4e0a\\u67b6\\u65e5\\u671f', '\\u4e0a\\u67b6\\u65f6\\u95f4'],
          ['\\u8bc4\\u8bba\\u6570', '\\u5f00\\u5e97', '\\u7c7b\\u76ee', '\\u5e74\\u9500\\u91cf'],
        );
        return /^\\d{4}[-/.]\\d{2}[-/.]\\d{2}/.test(value) ? value : '';
      };
      const getTopDates = () => Array.from(document.querySelectorAll('a.fx-offer-card[href*="detail.1688.com/offer/"]'))
        .slice(0, 8)
        .map((card) => parseDateOnly(getListedTimeText(card)))
        .filter(Boolean);
      const isDescending = (dates) => {
        if (dates.length < 2) return false;
        for (let i = 1; i < dates.length; i += 1) {
          if (dates[i - 1] < dates[i]) return false;
        }
        return true;
      };

      window.scrollTo({ top: 0, behavior: 'instant' });
      await sleep(400);

      const main = Array.from(document.querySelectorAll('span.category-item__trigger'))
        .find((el) => normalize(el.textContent) === '${toUnicodeEscape(args.mainCategory)}' && isVisible(el));
      if (!main) throw new Error('main category not found: ${toUnicodeEscape(args.mainCategory)}');
      main.scrollIntoView({ block: 'center' });
      for (const type of ['mouseenter', 'mouseover', 'mousedown', 'mouseup', 'click']) {
        main.dispatchEvent(new MouseEvent(type, { bubbles: true }));
      }
      await sleep(1200);
      const sub = Array.from(document.querySelectorAll('.fx-cascader-menu-item'))
        .find((el) => normalize(el.textContent) === '${toUnicodeEscape(args.subCategory)}' && isVisible(el));
      if (!sub) throw new Error('sub category not found: ${toUnicodeEscape(args.subCategory)}');
      sub.scrollIntoView({ block: 'center' });
      for (const type of ['pointerdown', 'mousedown', 'mouseup', 'click']) {
        sub.dispatchEvent(new MouseEvent(type, { bubbles: true }));
      }
      await sleep(2500);

      const sort = Array.from(document.querySelectorAll('.sort-filter-trigger'))
        .find((el) => normalize(el.textContent) === '${toUnicodeEscape(args.sortText)}' && isVisible(el));
      if (!sort) throw new Error('sort trigger not found: ${toUnicodeEscape(args.sortText)}');
      for (let attempt = 0; attempt < 3; attempt += 1) {
        const sortClass = String(sort.className || '');
        const topDates = getTopDates();
        if (sortClass.includes('actived') && isDescending(topDates)) break;
        sort.click();
        await sleep(2500);
      }

      const page1Item = document.querySelector('li.ant-pagination-item-1, li[title="1"]');
      const currentPage = normalize(document.querySelector('.ant-pagination-item-active')?.textContent || '');
      if (page1Item && currentPage !== '1') {
        const previousFirstHref = document.querySelector('a.fx-offer-card[href*="detail.1688.com/offer/"]')?.href || '';
        page1Item.click();
        const started = Date.now();
        while (Date.now() - started < 20000) {
          const active = normalize(document.querySelector('.ant-pagination-item-active')?.textContent || '');
          const firstHref = document.querySelector('a.fx-offer-card[href*="detail.1688.com/offer/"]')?.href || '';
          if (active === '1' && firstHref && firstHref !== previousFirstHref) break;
          await sleep(300);
        }
        await sleep(state.waitMs);
      }

      return {
        activePage: normalize(document.querySelector('.ant-pagination-item-active')?.textContent || ''),
        sortClass: String(sort.className || ''),
        topDates: getTopDates(),
      };
    })(JSON.parse(${JSON.stringify(JSON.stringify(state))})))`;

    const setupResult = await send("Runtime.evaluate", {
      expression: setupExpression,
      awaitPromise: true,
      returnByValue: true,
    });
    if (setupResult.exceptionDetails) {
      throw new Error(setupResult.result?.description || "setup expression failed");
    }

    const waitReadyExpression = `((async (state) => {
      const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const normalize = (text) => (text || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
      const collect = () => {
        const cards = Array.from(document.querySelectorAll('a.fx-offer-card[href*="detail.1688.com/offer/"]')).slice(0, state.pageSize);
        const rows = cards.map((card) => {
          const pluginText = normalize(card.querySelector('.plugin-offer-search-card')?.textContent || '');
          const fullText = normalize(card.innerText || '');
          return {
            plugin: !!pluginText,
            listed: pluginText.includes('\\u4e0a\\u67b6\\u65e5\\u671f') || fullText.includes('\\u4e0a\\u67b6\\u65e5\\u671f'),
            sales: pluginText.includes('\\u5e74\\u9500\\u91cf') || fullText.includes('\\u5e74\\u9500\\u91cf'),
          };
        });
        return {
          pageCurrent: normalize(document.querySelector('.ant-pagination-item-active')?.textContent || '1'),
          total: rows.length,
          pluginCount: rows.filter((row) => row.plugin).length,
          listedCount: rows.filter((row) => row.listed).length,
          salesCount: rows.filter((row) => row.sales).length,
        };
      };

      let snapshot = collect();
      const started = Date.now();
      while (Date.now() - started < state.waitMs) {
        snapshot = collect();
        if (
          snapshot.total >= state.pageSize &&
          snapshot.pluginCount >= Math.max(state.pageSize - 5, 1) &&
          snapshot.listedCount >= Math.max(state.pageSize - 5, 1) &&
          snapshot.salesCount >= Math.max(state.pageSize - 5, 1)
        ) {
          return { ok: true, snapshot };
        }
        await sleep(500);
      }
      return { ok: false, snapshot };
    })(JSON.parse(${JSON.stringify(JSON.stringify(state))})))`;

    const extractExpression = `(() => {
      const normalize = (text) => (text || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
      const getProvinceLike = (text) => {
        const source = normalize(text);
        if (!source) return '';
        const patterns = [
          /([\\u4e00-\\u9fa5]{2,8}(?:\\u7701|\\u5e02|\\u81ea\\u6cbb\\u533a|\\u7279\\u522b\\u884c\\u653f\\u533a))/,
          /([\\u4e00-\\u9fa5]{2,8}(?:\\u5730\\u533a|\\u76df))/,
          /([\\u4e00-\\u9fa5]{2,8}(?:\\u53bf|\\u533a))/,
        ];
        for (const pattern of patterns) {
          const match = source.match(pattern);
          if (match) return match[1];
        }
        return '';
      };
      const extractTaggedValue = (source, labels, endLabels) => {
        const text = normalize(source);
        for (const label of labels) {
          const index = text.indexOf(label);
          if (index === -1) continue;
          let value = text.slice(index + label.length);
          let endPos = value.length;
          for (const endLabel of endLabels) {
            const endIndex = value.indexOf(endLabel);
            if (endIndex !== -1 && endIndex < endPos) endPos = endIndex;
          }
          value = normalize(value.slice(0, endPos).replace(/^[:\\uFF1A]\\s*/, ''));
          if (value) return value;
        }
        return '';
      };
      const getPluginSource = (card) => {
        const pluginText = normalize(card.querySelector('.plugin-offer-search-card')?.textContent || '');
        const fullText = normalize(card.innerText || '');
        return pluginText || fullText;
      };
      const getListedTimeText = (card) => {
        const value = extractTaggedValue(
          getPluginSource(card),
          ['\\u4e0a\\u67b6\\u65e5\\u671f', '\\u4e0a\\u67b6\\u65f6\\u95f4'],
          ['\\u8bc4\\u8bba\\u6570', '\\u5f00\\u5e97', '\\u7c7b\\u76ee', '\\u5e74\\u9500\\u91cf'],
        );
        return /^\\d{4}[-/.]\\d{2}[-/.]\\d{2}/.test(value) ? value : '';
      };
      const getAnnualSales = (card) => {
        const value = extractTaggedValue(
          getPluginSource(card),
          ['\\u5e74\\u9500\\u91cf', '\\u5e74\\u9500', '\\u5e74\\u552e'],
          ['\\u4e0a\\u67b6\\u65e5\\u671f', '\\u4e0a\\u67b6\\u65f6\\u95f4', '\\u8bc4\\u8bba\\u6570', '\\u5f00\\u5e97', '\\u7c7b\\u76ee'],
        );
        if (!value || value === '-' || value === '\\u91cf:-') return '';
        return value.replace(/^\\u91cf[:\\uFF1A]?/, '');
      };

      const cards = Array.from(document.querySelectorAll('a.fx-offer-card[href*="detail.1688.com/offer/"]')).slice(0, ${args.pageSize});
      const pageCurrent = normalize(document.querySelector('.ant-pagination-item-active')?.textContent || '1');
      const sort = Array.from(document.querySelectorAll('.sort-filter-trigger')).find((el) => normalize(el.textContent) === ${JSON.stringify(args.sortText)});

      return {
        pageCurrent,
        firstHref: cards[0]?.href || '',
        sortClass: sort ? String(sort.className || '') : '',
        rows: cards.map((card) => {
          const title = normalize(card.querySelector('.offer-body__title')?.textContent || card.getAttribute('title') || '');
          const supplier = normalize(card.querySelector('.shop-name, .company-name')?.textContent || '');
          const image = card.querySelector('img.offer-header__image, img[data-src], img');
          const imageUrl = image?.currentSrc || image?.getAttribute('src') || image?.getAttribute('data-src') || '';
          const price = normalize(card.querySelector('.fx-offer-card-v2-price, .price-now')?.textContent || '').replace(/^\\uFFE5\\s*/, '');
          const deliveryInfo = normalize(card.querySelector('.fx-offer-card-v2-delivery-info')?.textContent || '');
          const source = getPluginSource(card);
          const categoryText = extractTaggedValue(
            source,
            ['\\u7c7b\\u76ee'],
            ['\\u5e74\\u9500\\u91cf', '\\u5e74\\u9500', '\\u5e74\\u552e', '\\u4e0a\\u67b6\\u65e5\\u671f', '\\u4e0a\\u67b6\\u65f6\\u95f4', '\\u8bc4\\u8bba\\u6570', '\\u5f00\\u5e97'],
          );
          return {
            page: pageCurrent,
            category: normalize(categoryText || (${JSON.stringify(args.mainCategory)} + ' > ' + ${JSON.stringify(args.subCategory)})),
            title,
            listedTime: getListedTimeText(card),
            annualSales: getAnnualSales(card),
            productUrl: card.href || '',
            imageUrl,
            price,
            supplier,
            origin: getProvinceLike(deliveryInfo) || getProvinceLike(source) || getProvinceLike(supplier),
          };
        }),
      };
    })()`;

    const rows = [];
    const seen = new Set();
    const pageStats = [];

    for (let pageIndex = 1; pageIndex <= args.pages && rows.length < args.maxItems; pageIndex += 1) {
      const readyResult = await send("Runtime.evaluate", {
        expression: waitReadyExpression,
        awaitPromise: true,
        returnByValue: true,
      });
      if (readyResult.exceptionDetails) {
        throw new Error(readyResult.result?.description || "waitReady expression failed");
      }
      const ready = readyResult.result?.value;
      if (!ready?.ok) {
        throw new Error(`plugin fields not ready: ${JSON.stringify(ready?.snapshot || {})}`);
      }

      const extractResult = await send("Runtime.evaluate", {
        expression: extractExpression,
        returnByValue: true,
      });
      if (extractResult.exceptionDetails) {
        throw new Error(extractResult.result?.description || "extract expression failed");
      }
      const payload = extractResult.result?.value;
      if (!payload?.rows?.length) throw new Error(`no rows extracted on loop ${pageIndex}`);
      if (!String(payload.sortClass || "").includes("actived")) {
        throw new Error(`sort is not active on page ${payload.pageCurrent}`);
      }

      let added = 0;
      let listedNonEmpty = 0;
      let salesNonEmpty = 0;
      for (const row of payload.rows) {
        if (row.listedTime) listedNonEmpty += 1;
        if (row.annualSales) salesNonEmpty += 1;
        const key = row.productUrl;
        if (!key || seen.has(key)) continue;
        seen.add(key);
        rows.push(row);
        added += 1;
        if (rows.length >= args.maxItems) break;
      }

      pageStats.push({
        page: payload.pageCurrent,
        added,
        listedNonEmpty,
        salesNonEmpty,
        firstDate: payload.rows[0].listedTime || "",
        readySnapshot: ready.snapshot,
      });
      console.error(
        `page=${payload.pageCurrent} added=${added} listed=${listedNonEmpty}/${payload.rows.length} sales=${salesNonEmpty}/${payload.rows.length} first=${payload.rows[0].listedTime || "-"}`,
      );

      if (pageIndex >= args.pages || rows.length >= args.maxItems) break;

      const nextExpression = `((prevHref, waitMs) => new Promise((resolve) => {
        const normalize = (text) => (text || '').replace(/\\s+/g, ' ').trim();
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
          if (firstHref && firstHref !== prevHref) {
            clearInterval(timer);
            setTimeout(() => resolve({ ok: true, firstHref, current }), waitMs);
            return;
          }
          if (Date.now() - started > 20000) {
            clearInterval(timer);
            resolve({ ok: false, reason: 'timeout', firstHref, current });
          }
        }, 300);
      }))(${JSON.stringify(payload.firstHref)}, ${args.waitMs})`;

      const nextResult = await send("Runtime.evaluate", {
        expression: nextExpression,
        awaitPromise: true,
        returnByValue: true,
      });
      if (nextResult.exceptionDetails) {
        throw new Error(nextResult.result?.description || "next expression failed");
      }
      const nextPayload = nextResult.result?.value;
      if (!nextPayload?.ok) {
        throw new Error(`next page failed after ${payload.pageCurrent}: ${nextPayload?.reason || "unknown"}`);
      }
    }

    const outputPath = path.resolve(args.output);
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    const headers = ["页码", "类目", "商品名", "上架时间", "年销量", "商品原链接", "商品图片链接", "价格", "供货商", "所在地（近似）"];
    const csvRows = rows.map((row) => ({
      "页码": row.page || "",
      "类目": row.category || "",
      "商品名": row.title || "",
      "上架时间": row.listedTime || "",
      "年销量": row.annualSales || "",
      "商品原链接": row.productUrl || "",
      "商品图片链接": row.imageUrl || "",
      "价格": row.price || "",
      "供货商": row.supplier || "",
      "所在地（近似）": row.origin || "",
    }));
    fs.writeFileSync(outputPath, toCsv(csvRows, headers), "utf8");
    const debugPath = outputPath.replace(/\.csv$/i, ".debug.json");
    fs.writeFileSync(
      debugPath,
      JSON.stringify({ setup: setupResult.result?.value || {}, total: rows.length, pageStats }, null, 2),
      "utf8",
    );

    console.log(JSON.stringify({ output: outputPath, debug: debugPath, total: rows.length, pageStats }, null, 2));
  } finally {
    ws.close();
  }
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});




