const endpoint = 'http://127.0.0.1:9222';

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

async function main() {
  const { ws, send } = await connect();
  try {
    const expression = `(async () => {
      const normalize = (s) => (s || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
      const collect = () => {
        const cards = Array.from(document.querySelectorAll('a.fx-offer-card[href*="detail.1688.com/offer/"]')).slice(0, 50);
        const rows = cards.map((card, idx) => {
          const pluginText = normalize(card.querySelector('.plugin-offer-search-card')?.textContent || '');
          const fullText = normalize(card.innerText || '');
          return {
            idx,
            href: card.href || '',
            hasPlugin: !!pluginText,
            pluginLen: pluginText.length,
            hasListed: pluginText.includes('上架日期') || fullText.includes('上架日期'),
            hasSales: pluginText.includes('年销量') || fullText.includes('年销量'),
          };
        });
        return {
          page: normalize(document.querySelector('.ant-pagination-item-active')?.textContent || ''),
          pluginCount: rows.filter((r) => r.hasPlugin).length,
          listedCount: rows.filter((r) => r.hasListed).length,
          salesCount: rows.filter((r) => r.hasSales).length,
          sample: rows.slice(0, 12),
        };
      };
      const before = collect();
      for (let y = 0; y < document.body.scrollHeight; y += 700) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 250));
      }
      window.scrollTo(0, 0);
      await new Promise((r) => setTimeout(r, 1000));
      const after = collect();
      return { before, after };
    })()`;
    const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    console.log(JSON.stringify(result.result.value, null, 2));
  } finally {
    ws.close();
  }
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
