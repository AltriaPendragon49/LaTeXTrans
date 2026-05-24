/**
 * RAG Terminology - E2E 验收测试 (完整版)
 * 用法: node scripts/tests/rag-e2e-test.mjs
 */
import { chromium } from 'playwright';

const BASE = 'https://paperx.niutrans.com';
const API = 'https://api.latextrans.online';
const { TEST_IDENTIFIER, TEST_PASSWORD } = process.env;
if (!TEST_IDENTIFIER || !TEST_PASSWORD) {
  console.error('请设置环境变量 TEST_IDENTIFIER 和 TEST_PASSWORD');
  process.exit(1);
}
const R = [];
function ok(n) { R.push(`✅ ${n}`); console.log('  ✅ ' + n); }
function w(n, r) { R.push(`⚠️ ${n}: ${r}`); console.log('  ⚠️ ' + n + ': ' + r); }
function f(n, r) { R.push(`❌ ${n}: ${r}`); console.log('  ❌ ' + n + ': ' + r); }

async function waitForContent(page, minChars = 100, maxWait = 15000) {
  const start = Date.now();
  while (Date.now() - start < maxWait) {
    const len = await page.evaluate(() => document.body.innerText.length);
    if (len >= minChars) return len;
    await page.waitForTimeout(500);
  }
  return await page.evaluate(() => document.body.innerText.length);
}

(async () => {
  console.log('═══════════════════════════════════════════');
  console.log('  RAG Terminology E2E 验收测试');
  console.log('═══════════════════════════════════════════');

  const fs = await import('fs');
  fs.mkdirSync('artifacts/e2e', { recursive: true });

  const browser = await chromium.launch({
    channel: 'chrome',
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--no-proxy-server'],
  });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'zh-CN' });
  const page = await ctx.newPage();

  try {
    // ==================== 1. 登录 ====================
    console.log('\n--- 1. 登录 ---');
    await page.goto(BASE + '/login', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'artifacts/e2e/01-login.png', fullPage: true });

    const pwInput = await page.$('input[type="password"]');
    const idInput = await page.$('input[type="text"]') || await page.$('input:not([type="password"])');
    if (idInput && pwInput) {
      await idInput.fill(TEST_IDENTIFIER);
      await pwInput.fill(TEST_PASSWORD);
      const loginBtn = await page.$('button');
      if (loginBtn) { await loginBtn.click(); }
      await page.waitForTimeout(5000);
      await page.waitForLoadState('networkidle').catch(() => {});
      await page.waitForTimeout(2000);
    }

    const url = page.url();
    if (!url.includes('/login')) {
      ok('登录成功');
      await page.screenshot({ path: 'artifacts/e2e/02-after-login.png', fullPage: true });
    } else {
      const errText = await page.evaluate(() => document.body.innerText);
      f('登录', `停留在登录页 - "${errText.slice(0, 150)}"`);
    }

    // ==================== 2. 术语管理页面 ====================
    console.log('\n--- 2. 术语管理页面 (/admin/rag-terminology) ---');
    await page.goto(BASE + '/admin/rag-terminology', { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
    const len2 = await waitForContent(page, 50, 12000);
    await page.screenshot({ path: 'artifacts/e2e/03-admin-terms.png', fullPage: true });

    if (page.url().includes('/login')) {
      w('术语管理', '需要登录权限');
    } else if (len2 > 50) {
      ok('术语管理页面加载成功');
      const bt = await page.evaluate(() => document.body.innerText.slice(0, 400));
      console.log('  内容: ' + bt.replace(/\n/g, ' | '));
    } else {
      w('术语管理', '页面空白 (SPA可能未渲染，body长度=' + len2 + ')');
    }

    // ==================== 3. 个人术语工作区 ====================
    console.log('\n--- 3. 个人术语工作区 (/workspace/glossary) ---');
    await page.goto(BASE + '/workspace/glossary', { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
    const len3 = await waitForContent(page, 30, 10000);
    await page.screenshot({ path: 'artifacts/e2e/04-workspace.png', fullPage: true });

    if (page.url().includes('/login')) {
      w('术语工作区', '需要登录');
    } else if (len3 > 30) {
      ok('术语工作区页面加载成功');
    } else {
      w('术语工作区', '页面空白 (body长度=' + len3 + ')');
    }

    // ==================== 4. 工具中心 ====================
    console.log('\n--- 4. 工具中心 ---');
    await page.goto(BASE + '/tools-hub', { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
    const len4 = await waitForContent(page, 50, 10000);
    await page.screenshot({ path: 'artifacts/e2e/05-tools-hub.png', fullPage: true });

    if (len4 > 50) {
      ok('工具中心页面加载成功');
    } else {
      w('工具中心', '页面空白 (body长度=' + len4 + ')');
    }

    // ==================== 5. 浏览器端 API 验证 ====================
    console.log('\n--- 5. 浏览器端 API 验证 ---');
    const apiResults = await page.evaluate(async (apiBase) => {
      const r = [];
      try { const resp = await fetch(apiBase + '/api/health'); r.push('health: ' + (await resp.json()).status); } catch(e) { r.push('health: FAIL'); }
      try { const resp = await fetch(apiBase + '/api/terminology/domains'); const d = await resp.json(); r.push('domains: ' + d.domains.length); } catch(e) { r.push('domains: FAIL'); }
      try { const resp = await fetch(apiBase + '/api/terminology/terms?page_size=5'); const d = await resp.json(); r.push('terms: total=' + d.total); } catch(e) { r.push('terms: FAIL'); }
      try {
        const resp = await fetch(apiBase + '/api/terminology/glossary/lookup', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chunk_text: 'inverted index and dense retrieval improve search', source_lang: 'en', target_lang: 'zh' }),
        });
        const d = await resp.json();
        r.push('glossary: ' + d.match_count + ' matches, block=' + d.glossary_block);
      } catch(e) { r.push('glossary: FAIL - ' + e.message); }
      return r;
    }, API);

    for (const r of apiResults) {
      if (r.includes('FAIL')) f('API: ' + r.split(':')[0], r);
      else ok(r);
    }

    // ==================== 6. 检索质量 ====================
    console.log('\n--- 6. 术语检索质量验证 ---');
    const cases = [
      ['inverted index improves search', '倒排索引'],
      ['dense retrieval and sparse retrieval for hybrid search', '稠密/稀疏/混合检索'],
      ['NDCG used for document ranking evaluation', '文档排序/NDCG'],
      ['query expansion and relevance feedback in information retrieval', '查询扩展/相关反馈'],
      ['cross-modal alignment with multimodal transformers', '跨模态对齐'],
      ['functional analysis in mathematics', '泛函分析'],
    ];
    for (const [text, label] of cases) {
      const r = await page.evaluate(async ({ api, chunk }) => {
        const resp = await fetch(api + '/api/terminology/glossary/lookup', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chunk_text: chunk, source_lang: 'en', target_lang: 'zh' }),
        });
        const d = await resp.json();
        return d.match_count;
      }, { api: API, chunk: text });
      if (r > 0) ok(label + ': ' + r + ' 匹配');
      else w(label, '0 匹配（跨领域或未覆盖术语）');
    }

    // ==================== 汇总 ====================
    console.log('\n═══════════════════════════════════════════');
    const total = R.length;
    const passes = R.filter(r => r.startsWith('✅')).length;
    const warns = R.filter(r => r.startsWith('⚠️')).length;
    const fails = R.filter(r => r.startsWith('❌')).length;
    console.log('  测试汇总: ' + passes + ' 通过 / ' + warns + ' 警告 / ' + fails + ' 失败 / ' + total + ' 总计');
    console.log('═══════════════════════════════════════════');
    for (const r of R) console.log(r);
    console.log('\n截图保存在 artifacts/e2e/');

    console.log('\n浏览器保持 8 秒...');
    await page.waitForTimeout(8000);

    if (fails > 0) process.exitCode = 1;
  } catch (e) {
    console.error('错误:', e.message);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
