// Captura cada HTML a PNG 1920x1080 (1280x720 CSS a escala 1.5).
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 });
  for (const [html, png] of jobs) {
    await pg.goto('file://' + html);
    await pg.evaluate(() => document.fonts.ready);
    await pg.screenshot({ path: png });
  }
  await b.close();
})();
