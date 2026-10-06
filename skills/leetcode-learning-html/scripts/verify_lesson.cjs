const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),vm=require('node:vm'),{pathToFileURL,fileURLToPath}=require('node:url');
const args=process.argv.slice(2),option=name=>{const i=args.indexOf(name);return i<0?undefined:args[i+1]},file=path.resolve(args[0]||'');
const {chromium}=require(option('--playwright')||'playwright');let browser;
(async()=>{
 const html=fs.readFileSync(file,'utf8');
 assert(!/\b(?:localStorage|sessionStorage|indexedDB)\b|document\.cookie/.test(html),'Learning data must not use browser storage');
 for(const script of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g))if(!/application\/json/.test(script[1]))new vm.Script(script[2]);
 browser=await chromium.launch({headless:true,...(option('--browser')?{executablePath:option('--browser')}:{})});
 const context=await browser.newContext(),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.stack));page.setDefaultTimeout(5000);
 await page.goto(pathToFileURL(file).href);const lesson=await page.locator('#lessonData').evaluate(e=>JSON.parse(e.textContent));
 if(lesson.home){const link=new URL(lesson.home,pathToFileURL(file));link.hash='';link.search='';assert(fs.existsSync(fileURLToPath(link)),'Missing local home destination');assert.match(await page.locator('#homeLink').innerText(),/返回主页/);}else assert.equal(await page.locator('#homeLink').getAttribute('href'),'#overview');
 for(const index of [5,4,3,2,1,0]){await page.locator(`[data-action="module"][data-module="${index}"]`).click();assert.equal(await page.locator('#moduleNav .active').getAttribute('data-module'),String(index));}
 await page.locator('[data-module="3"]').click();let frames=0,answers=0;
 for(const c of lesson.cases){await page.locator('select[data-action="case"]').selectOption(c.id);
  for(let i=0;i<c.frames.length;i++){
   frames++;const labels=await page.locator('[data-action="answer"]').allTextContents();
   for(const label of labels){await page.getByRole('button',{name:label,exact:true}).click();assert.equal(await page.locator('#referenceDialog').evaluate(e=>e.open),false);answers++;}
   if(i<c.frames.length-1)await page.locator('[data-action="step"][data-delta="1"]').click();
  }
  if(c.frames.length>1){await page.locator('[data-action="step"][data-delta="-1"]').click();assert.match(await page.locator('.step-count').innerText(),new RegExp(`^${c.frames.length-1} /`));}
 }
 await page.locator('[data-module="4"]').click();assert.deepEqual(await page.locator('input[data-slot]').evaluateAll(es=>es.map(e=>e.value)),lesson.code.slots.map(()=>''));
 const slot=lesson.code.slots[0],field=page.locator(`[data-slot="${slot.id}"]`);await field.fill('wrong expression');await page.locator('[data-action="check-slots"]').click();assert.equal(await field.inputValue(),'wrong expression');
 await page.locator('[data-action="reference"]').click();assert.equal(await field.isVisible(),false);await page.locator('[data-action="close-reference"]').click();assert.equal(await field.inputValue(),'wrong expression');
 for(const s of lesson.code.slots)await page.locator(`[data-slot="${s.id}"]`).fill(s.accepted[0]);await page.locator('[data-action="check-slots"]').click();assert.equal(await page.locator('input[data-slot].valid').count(),lesson.code.slots.length);
 await page.locator('[data-module="5"]').click();let draft='class Solution:\n    def solve(self):\n        pass # 自己的草稿';await page.locator('textarea[data-draft="main"]').fill(draft);
 await page.locator('[data-action="reference"]').click();assert.equal(await page.locator('textarea.editor').isVisible(),false);await page.locator('[data-action="close-reference"]').click();assert.equal(await page.locator('textarea.editor').inputValue(),draft);
 await page.locator('[data-module="0"]').click();await page.locator('[data-module="5"]').click();assert.equal(await page.locator('textarea.editor').inputValue(),draft);
 await page.locator('[data-action="subtab"][data-subtab="transfer"]').click();assert.equal(await page.locator('textarea.editor').count(),0);
 for(const c of lesson.transfer.cases){await page.locator('select[data-action="case"]').selectOption(c.id);for(let i=1;i<c.frames.length;i++)await page.locator('[data-action="step"][data-delta="1"]').click();}
 await page.locator('[data-action="transfer-mode"][data-mode="code"]').click();assert.equal(await page.locator('textarea[data-draft="transfer"]').isEnabled(),true);
 assert.equal(await page.locator('textarea[data-draft="transfer"]').inputValue(),lesson.transfer.starter);assert.equal(await page.locator('.code-trace').count(),0);assert.equal(await page.locator('.array-view').count(),0);
 for(const width of [390,1440]){
  await page.setViewportSize({width,height:1000});for(const i of [0,3,4,5]){await page.locator(`[data-module="${i}"]`).click();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Overflow in module ${i} at ${width}px`);}
  await page.locator('[data-module="0"]').click();await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:file.replace(/\.html$/i,`-${width}.png`),fullPage:true});
 }
 await page.reload();assert.equal(await page.locator('#moduleNav .active').getAttribute('data-module'),'0');await page.locator('[data-module="4"]').click();assert.deepEqual(await page.locator('input[data-slot]').evaluateAll(es=>es.map(e=>e.value)),lesson.code.slots.map(()=>''));
 await page.locator('[data-module="5"]').click();assert.equal(await page.locator('textarea.editor').inputValue(),lesson.code.starter);
 await page.goto('about:blank');await page.goBack();await page.waitForFunction(()=>document.querySelector('#moduleNav .active')?.dataset.module==='0');assert.equal(await page.locator('#moduleNav .active').getAttribute('data-module'),'0');
 assert.deepEqual(errors,[]);await browser.close();console.log(JSON.stringify({file,modules:6,frames,answerChoices:answers,manualSlots:lesson.code.slots.length,draftPreservation:true,newVisitResets:true,widths:[390,1440],errors:[]},null,2));
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exitCode=1});
