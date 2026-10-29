// usage:
//   node render.mjs stills <cues.json> <out_dir> t1 t2 ...   -> PNG stills for checking
//   node render.mjs video  <cues.json> <out.mp4> <duration>  -> silent 30 fps H.264
import { createRequire } from 'module';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const require = createRequire('/opt/node22/lib/node_modules/');
let pw;
try { pw = require('playwright'); } catch { pw = require('/opt/node-tools/node_modules/playwright'); }

const [mode, cuesPath, out, ...rest] = process.argv.slice(2);
const here = path.dirname(fileURLToPath(import.meta.url));
const cues = JSON.parse(fs.readFileSync(cuesPath, 'utf8'));

const browser = await pw.chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
page.on('pageerror', e => console.error('PAGE ERROR', e.message));
await page.goto('file://' + path.join(here, 'scene.html'));
await page.evaluate(async c => { await window.ready; window.setCues(c); }, cues);

const frame = async (t, type = 'jpeg') => {
  const data = await page.evaluate(([t, type]) => {
    window.render(t);
    return document.getElementById('c').toDataURL(type === 'png' ? 'image/png' : 'image/jpeg', 0.93);
  }, [t, type]);
  return Buffer.from(data.split(',')[1], 'base64');
};

if (mode === 'stills') {
  fs.mkdirSync(out, { recursive: true });
  for (const t of rest.map(Number)) fs.writeFileSync(path.join(out, `t${t.toFixed(2)}.png`), await frame(t, 'png'));
} else {
  const fps = 30, n = Math.ceil(Number(rest[0]) * fps);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < n; i++) {
    const buf = await frame(i / fps);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${n}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
}
await browser.close();
