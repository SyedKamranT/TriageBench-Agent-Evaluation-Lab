import puppeteer from 'puppeteer-core';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const executablePath = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);
const browser = await puppeteer.launch({executablePath, headless:true});
let checks=0;
try {
  const page=await browser.newPage();const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'reduce'}]);
  await page.goto(new URL('./index.html',import.meta.url).href);
  for(const width of [320,375,768,1280,1440,1920]) {
    await page.setViewport({width,height:900});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));checks++;
  }
  assert.equal(await page.$$eval('.case',e=>e.length),20);checks++;
  assert.equal(await page.$$eval('.case.pass',e=>e.length),17);checks++;
  await page.click('[data-version=v1]');
  assert.equal(await page.$$eval('.case.pass',e=>e.length),8);checks++;
  assert.equal(await page.$eval('#passrate',e=>e.textContent),'40');checks++;
  assert.match(await page.$eval('#case-title',e=>e.textContent),/Baseline/);checks++;
  await page.click('[data-version=v2]');await page.click('[data-id=G05]');
  const output=JSON.parse(await page.$eval('#case-output',e=>e.textContent));
  assert.equal(output.tool_calls[0].arguments.ticket_id,'CS-9999');checks++;
  assert('error' in output && 'handoff' in output && 'evidence_ids' in output);checks++;
  await page.click('details summary');
  assert.equal(await page.$eval('details',e=>e.open),true);checks++;
  assert(await page.$eval('#case-output',e=>e.getBoundingClientRect().height>0));checks++;
  await page.click('#tour');assert.equal(await page.$eval('#playback',e=>e.hidden),false);checks++;
  await page.keyboard.press('Escape');assert.equal(await page.$eval('#playback',e=>e.hidden),true);checks++;
  assert.equal(await page.$eval('body',e=>e.classList.contains('capture')),false);checks++;
  assert.deepEqual(errors,[]);checks++;
  await page.setJavaScriptEnabled(false);await page.reload();
  assert.match(await page.$eval('#result',e=>e.textContent),/85/);checks++;
  console.log(`${checks} browser checks passed. No live model evaluation performed.`);
} finally { await browser.close(); }
