#!/usr/bin/env node
// Проверка полосы: ошибки JS, плавность анимации, скриншот.
//   node check.js gazeta.html [скриншот.png]
// Выход 0 — всё в порядке, 1 — есть ошибки или анимация медленная.
const fs = require('fs');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { console.log('Playwright не найден — проверка пропущена.'); process.exit(0); }

(async () => {
  const file = process.argv[2], shot = process.argv[3];
  if (!file) { console.log('Использование: node check.js gazeta.html [shot.png]'); process.exit(2); }
  const html = '<!doctype html><meta charset="utf-8">' + fs.readFileSync(file, 'utf8');
  const b = await chromium.launch(); let bad = false;
  for (const [w, h, dpr] of [[1200, 1400, 2], [400, 800, 3]]) {
    const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: dpr });
    const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    p.on('console', m => { if (m.type() === 'error' && !/ERR_|Failed to load resource/.test(m.text())) errs.push(m.text()); });
    await p.setContent(html, { waitUntil: 'load' });
    await p.waitForTimeout(1500);
    const info = await p.evaluate(() => {
      const arts = [...document.querySelectorAll('.art')];
      return { arts: arts.length, drawn: arts.filter(a => a.querySelector('canvas')).length, wide: document.documentElement.scrollWidth > window.innerWidth + 1 };
    });
    const fr = await p.evaluate(() => new Promise(res => { const ts = []; let l = performance.now(); function f(n) { ts.push(n - l); l = n; if (ts.length < 120) requestAnimationFrame(f); else { ts.sort((a, b) => a - b); res({ med: ts[60], p95: ts[114] }); } } requestAnimationFrame(f); }));
    const ok = !errs.length && info.drawn === info.arts && !info.wide && fr.med <= 20;
    if (!ok) bad = true;
    console.log(`${w}px: ${ok ? 'OK' : 'ПРОБЛЕМА'} · иллюстраций ${info.drawn}/${info.arts} · кадр медиана ${fr.med.toFixed(1)} мс, p95 ${fr.p95.toFixed(1)} мс${info.wide ? ' · ГОРИЗОНТАЛЬНАЯ ПРОКРУТКА' : ''}`);
    errs.forEach(e => console.log('  ошибка: ' + e));
    if (shot && w === 1200) await p.screenshot({ path: shot, fullPage: true });
    await p.close();
  }
  await b.close();
  process.exit(bad ? 1 : 0);
})();
