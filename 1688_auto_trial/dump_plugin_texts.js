const endpoint = 'http://127.0.0.1:9222';

async function main() {
  const targets = await (await fetch(endpoint + '/json/list')).json();
  const page = targets.find((t) => t.type === 'page' && String(t.url || '').includes('air.1688.com/app/channel-fe/search/index.html'));
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
  const expr = `(() => {
    const normalize = (s) => (s || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
    return Array.from(document.querySelectorAll('a.fx-offer-card[href*="detail.1688.com/offer/"]')).slice(0,5).map((card, idx) => ({
      idx,
      title: normalize(card.querySelector('.offer-body__title')?.textContent || ''),
      pluginText: normalize(card.querySelector('.plugin-offer-search-card')?.textContent || ''),
      fullTextTail: normalize(card.innerText || '').slice(-200)
    }));
  })()`;
  const result = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  console.log(JSON.stringify(result.result.value, null, 2));
  ws.close();
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
