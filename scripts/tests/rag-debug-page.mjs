import { chromium } from 'playwright';

const { TEST_IDENTIFIER, TEST_PASSWORD } = process.env;
if (!TEST_IDENTIFIER || !TEST_PASSWORD) {
  console.error('请设置环境变量 TEST_IDENTIFIER 和 TEST_PASSWORD');
  process.exit(1);
}

const browser = await chromium.launch({
  channel: 'chrome', headless: false,
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--no-proxy-server'],
});
const page = await browser.newContext({ viewport: { width: 1440, height: 900 } }).then(c => c.newPage());

// Capture console errors
page.on('console', msg => { if (msg.type() === 'error') console.log('CONSOLE ERROR:', msg.text()); });
page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

// Login first
console.log('--- Login ---');
await page.goto('https://paperx.niutrans.com/login', { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForTimeout(2000);
const pw = await page.$('input[type="password"]');
const id = await page.$('input[type="text"]');
if (id && pw) {
  await id.fill(TEST_IDENTIFIER);
  await pw.fill(TEST_PASSWORD);
  await page.click('button');
  await page.waitForTimeout(5000);
  await page.waitForLoadState('networkidle').catch(() => {});
}
console.log('URL after login:', page.url());

// Check admin page
console.log('\n--- Admin Page ---');
await page.goto('https://paperx.niutrans.com/admin/rag-terminology', { waitUntil: 'networkidle', timeout: 30000 }).catch(e => console.log('goto failed:', e.message));
await page.waitForTimeout(5000);
console.log('URL:', page.url());
const html = await page.content();
console.log('HTML length:', html.length);
console.log('First 1000 chars:', html.slice(0, 1000));
console.log('Body innerText:', (await page.evaluate(() => document.body?.innerText || '(empty)')).slice(0, 300));

await page.screenshot({ path: 'artifacts/e2e/debug-admin.png', fullPage: true });
console.log('Screenshot saved.');

await page.waitForTimeout(3000);
await browser.close();
