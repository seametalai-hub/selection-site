const endpoint = 'http://127.0.0.1:9222';

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

  const currentRes = await send('Runtime.evaluate', {
    expression: `(() => ({ current: (document.querySelector('.ant-pagination-item-active')?.textContent || '').trim(), firstHref: document.querySelector('a.fx-offer-card[href*="detail.1688.com/offer/"]')?.href || '' }))()`,
    returnByValue: true,
  });
  const current = currentRes.result.value;

  const navExpr = `((prevHref) => new Promise((resolve) => {
    const item = document.querySelector('li.ant-pagination-item-1, li[title="1"]');
    if (!item) {
      resolve({ ok: false, reason: 'page1 button not found' });
      return;
    }
    item.click();
    const started = Date.now();
    const timer = setInterval(() => {
      const current = (document.querySelector('.ant-pagination-item-active')?.textContent || '').trim();
      const firstHref = document.querySelector('a.fx-offer-card[href*="detail.1688.com/offer/"]')?.href || '';
      if (current === '1' && firstHref && firstHref !== prevHref) {
        clearInterval(timer);
        setTimeout(() => resolve({ ok: true, current, firstHref }), 5000);
        return;
      }
      if (Date.now() - started > 20000) {
        clearInterval(timer);
        resolve({ ok: false, reason: 'timeout', current, firstHref });
      }
    }, 300);
  }))(${JSON.stringify(current.firstHref || '')})`;

  const navRes = await send('Runtime.evaluate', { expression: navExpr, awaitPromise: true, returnByValue: true });
  console.log(JSON.stringify({ before: current, after: navRes.result.value }, null, 2));
  ws.close();
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});
