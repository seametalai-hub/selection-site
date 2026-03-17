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
  const expr = `(async () => {
    const normalize = (s) => (s || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
    const card = document.querySelector('a.fx-offer-card[href*="detail.1688.com/offer/"]');
    if (!card) return { ok: false, reason: 'no card' };
    const read = () => ({
      pluginText: normalize(card.querySelector('.plugin-offer-search-card')?.textContent || ''),
      trendTexts: Array.from(card.querySelectorAll('*')).map(el => normalize(el.textContent || '')).filter(Boolean).filter(t => t.includes('趋势') || t.includes('采购助手')).slice(0,20)
    });
    const before = read();
    const trigger = Array.from(card.querySelectorAll('span,div,button')).find(el => normalize(el.textContent) === '趋势');
    if (trigger) {
      trigger.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
      trigger.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
      trigger.click();
    }
    await new Promise(r => setTimeout(r, 2000));
    const afterClick = read();
    card.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    card.scrollIntoView({ block: 'center' });
    await new Promise(r => setTimeout(r, 2000));
    const afterHover = read();
    return { ok: true, before, afterClick, afterHover };
  })()`;
  const result = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  console.log(JSON.stringify(result.result.value, null, 2));
  ws.close();
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
