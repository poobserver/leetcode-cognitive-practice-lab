(() => {
 'use strict';
 const lesson=JSON.parse(document.querySelector('#lessonData').textContent);
 const session={module:0,caseId:lesson.cases[0].id,step:0,answers:{},slots:{},drafts:{main:lesson.code.starter,transfer:lesson.transfer.starter},checks:{},subtab:'main',transferMode:'model'};
 const panel=document.querySelector('#learningPanel'),dialog=document.querySelector('#referenceDialog');
 const el=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e};
 const button=(text,action,attrs={})=>{const b=el('button','',text);b.type='button';b.dataset.action=action;Object.assign(b.dataset,attrs);return b};
 const list=values=>{const ul=el('ul');values.forEach(v=>ul.append(el('li','',v)));return ul};
 const display=value=>typeof value==='string'?value:JSON.stringify(value);
 document.title=`#${lesson.meta.id} ${lesson.meta.title} · 算法认知实验室`;
 document.querySelector('#problemMeta').textContent=`LEETCODE ${lesson.meta.id} / ${lesson.meta.difficulty}`;
 document.querySelector('#problemTitle').textContent=lesson.meta.title;
 document.querySelector('#modelHeadline').textContent=lesson.model.headline;
 document.querySelector('#problemSummary').textContent=lesson.problem.summary;
 document.querySelector('#publicSignature').textContent=lesson.problem.signature;
 document.querySelector('#constraints').replaceWith(Object.assign(list(lesson.problem.constraints),{id:'constraints'}));
 lesson.meta.tags.forEach(t=>document.querySelector('#problemTags').append(el('span','',t)));
 const source=document.querySelector('#problemSource');if(lesson.meta.source)source.href=lesson.meta.source;else source.hidden=true;
 if(lesson.home){const home=document.querySelector('#homeLink');home.href=lesson.home;home.textContent='← 返回主页';}
 lesson.problem.examples.forEach(example=>{const e=el('div','example');e.append(el('div','',example.input),el('div','',`输出：${example.output}`),el('p','',example.purpose));document.querySelector('#examples').append(e)});
 lesson.ladder.forEach((level,i)=>{const card=el('div',`level${level.current?' current':''}`);card.append(el('span','level-no',`LEVEL ${String(i+1).padStart(2,'0')}`),el('h3','',level.title),el('p','',level.detail),el('small','',level.problem));document.querySelector('#ladder').append(card)});
 for(const [key,title] of Object.entries({state:'状态 / 候选',contract:'函数 / 迭代契约',operation:'关键操作',invariant:'保持不变的事实',boundary:'边界与终止',answer:'答案位置'})){const dl=el('div');dl.append(el('dt','',title),el('dd','',lesson.model[key]));document.querySelector('#framework').append(dl)}
 for(const [key,title] of Object.entries({time:'时间复杂度',space:'额外空间'})){const dl=el('div');dl.append(el('dt','',title),el('dd','',lesson.model.complexity[key]));document.querySelector('#framework').append(dl)}
 const nav=document.querySelector('#moduleNav');lesson.stages.forEach((stage,i)=>nav.append(button(`${i+1} ${stage.title}`,'module',{module:i})));
 function questions(items,parent,keyPrefix){
  items.forEach((q,qi)=>{const key=`${keyPrefix}:${qi}`,box=el('div','question'),choices=el('div','choices');box.append(el('h3','',q.prompt));
   q.choices.forEach((choice,i)=>{const b=button(choice.text,'answer',{key,index:i});b._choice=choice;if(session.answers[key]?.index===i)b.classList.add(choice.correct?'correct':'wrong');choices.append(b)});
   const old=session.answers[key];box.append(choices,el('p',`feedback${old?(old.correct?' good':' bad'):''}`,old?.feedback||'先根据当前状态作出判断。'));parent.append(box);
  });
 }
 function visualization(view,parent){
  if(!view||view.type==='state')return;
  if(view.type==='array'){
   const strip=el('div','array-view');view.values.forEach((value,i)=>{const cell=el('div',`cell${view.active?.includes(i)?' active':''}${view.discarded?.includes(i)?' discarded':''}`);cell.append(el('strong','',display(value)),el('small','',`i=${i}`),el('span','pointers',Object.entries(view.pointers||{}).filter(([,index])=>index===i).map(([name])=>name).join(' · ')));strip.append(cell)});parent.append(strip);
   for(const [name,index] of Object.entries(view.pointers||{}))if(index<0||index>=view.values.length)parent.append(el('div','out-of-bounds',`${name}=${index}（数组范围外）`));
  }else if(view.type==='table'){
   const scroll=el('div','table-scroll'),table=el('table'),head=el('tr');view.columns.forEach(c=>head.append(el('th','',c)));table.append(head);view.rows.forEach((row,i)=>{const tr=el('tr',view.active?.includes(i)?'active':'');row.forEach(v=>tr.append(el('td','',display(v))));table.append(tr)});scroll.append(table);parent.append(scroll);
  }else{
   const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg'),scroll=el('div','diagram-scroll');svg.setAttribute('viewBox',`0 0 ${view.width||720} ${view.height||420}`);svg.setAttribute('role','img');svg.setAttribute('aria-label',view.label||'当前结构状态');
   const shape=(tag,attrs,text)=>{const s=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))s.setAttribute(k,v);if(text!==undefined)s.textContent=text;svg.append(s);return s};
   shape('defs',{});const defs=svg.lastChild,marker=document.createElementNS(ns,'marker');for(const [k,v] of Object.entries({id:'arrow',markerWidth:8,markerHeight:8,refX:7,refY:4,orient:'auto'}))marker.setAttribute(k,v);const arrow=document.createElementNS(ns,'path');arrow.setAttribute('d','M0 0 L8 4 L0 8Z');arrow.setAttribute('fill','#9caca2');marker.append(arrow);defs.append(marker);
   if(view.axis!==undefined)shape('line',{x1:view.axis,x2:view.axis,y1:10,y2:(view.height||420)-10,class:'axis'});
   const nodes=new Map(view.nodes.map(n=>[n.id,n]));
   view.edges.forEach(edge=>{const a=nodes.get(edge.from),b=nodes.get(edge.to),dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy),r=29;shape('line',{x1:a.x+dx/d*r,y1:a.y+dy/d*r,x2:b.x-dx/d*r,y2:b.y-dy/d*r,class:'diagram-edge','marker-end':'url(#arrow)',...(edge.dashed?{'stroke-dasharray':'5 5'}:{})});if(edge.label)shape('text',{x:(a.x+b.x)/2+8,y:(a.y+b.y)/2-9,class:'edge-label','text-anchor':'middle'},edge.label)});
   view.nodes.forEach(n=>{shape('circle',{cx:n.x,cy:n.y,r:27,class:`diagram-node ${n.status||''}`});shape('text',{x:n.x,y:n.y+5,'text-anchor':'middle',class:'node-label'},n.label);if(n.caption)shape('text',{x:n.x,y:n.y+45,'text-anchor':'middle',class:'edge-label'},n.caption)});scroll.append(svg);parent.append(scroll);
  }
 }
 function caseCard(parent,playback=false,transfer=false){
  const cases=transfer?lesson.transfer.cases:lesson.cases;
  if(!cases.some(c=>c.id===session.caseId)){session.caseId=cases[0].id;session.step=0;}
  const c=cases.find(c=>c.id===session.caseId);session.step=Math.min(session.step,c.frames.length-1);const frame=c.frames[session.step],card=el('div','card'),controls=el('div','controls'),select=el('select');select.setAttribute('aria-label','选择案例');select.dataset.action='case';
  cases.forEach(item=>{const option=el('option','',item.name);option.value=item.id;option.selected=item.id===c.id;select.append(option)});controls.append(select);card.append(controls,el('h3','',c.purpose),el('p','caption',`输入：${display(c.input)}`));
  visualization(frame.view,card);const state=el('div','state-grid');Object.entries(frame.state).forEach(([key,value])=>{const field=el('div');field.append(el('span','',key),el('strong','',display(value)));state.append(field)});card.append(state,el('p','operation',frame.operation),el('p','caption',frame.caption));
  if(playback){const previous=button('← 上一步','step',{delta:-1}),next=button('下一步 →','step',{delta:1});previous.disabled=session.step===0;next.disabled=session.step===c.frames.length-1;const bar=el('div','controls');bar.append(previous,el('span','step-count',`${session.step+1} / ${c.frames.length}`),next);card.append(bar)}
  if(playback&&!transfer&&session.module===3){const code=el('pre','code-trace');lesson.code.reference.split('\n').forEach((line,i)=>{const row=el('span',i+1===frame.line?'active':'',`${String(i+1).padStart(2,' ')}  ${line}`);row.dataset.line=i+1;code.append(row)});card.append(el('h3','','代码与当前状态对应'),code)}
  if(frame.question)questions([frame.question],card,`frame:${transfer?'transfer':'main'}:${c.id}:${session.step}`);parent.append(card);
 }
 function reviewButton(which){return button('查看参考代码','reference',{reference:which})}
 function codeSlots(){
  const card=el('div','card'),toolbar=el('div','coding-toolbar');toolbar.append(el('p','','根据契约独立填写；槽位没有默认答案。'),reviewButton('main'));card.append(toolbar);const skeleton=el('div','code-skeleton'),tokens=lesson.code.skeleton.split(/(\{\{[a-zA-Z]\w*\}\})/);
  tokens.forEach(token=>{const match=/^\{\{(\w+)\}\}$/.exec(token);if(!match){skeleton.append(document.createTextNode(token));return}const slot=lesson.code.slots.find(s=>s.id===match[1]),input=el('input');input.type='text';input.dataset.slot=slot.id;input.placeholder='请独立填写';input.setAttribute('aria-label',slot.label);input.title=slot.hint;input.autocomplete='off';input.spellcheck=false;input.value=session.slots[slot.id]||'';skeleton.append(input)});card.append(skeleton);
  const legend=el('div','slot-legend');lesson.code.slots.forEach(s=>{const d=el('div');d.append(el('strong','',s.label),el('small','',s.hint));legend.append(d)});const actions=el('div','controls');actions.append(button('检查槽位','check-slots'),button('清空槽位','clear-slots'));card.append(legend,actions,el('p','feedback',''));card.lastChild.id='slotFeedback';panel.append(card);
 }
 function independent(which){
  const code=which==='main'?lesson.code:lesson.transfer,card=el('div','card'),toolbar=el('div','coding-toolbar');toolbar.append(el('p','','从公开接口独立重写。当前页面内切换模块会保留草稿。'),reviewButton(which));card.append(toolbar);
  const editor=el('textarea','editor');editor.dataset.draft=which;editor.setAttribute('aria-label',which==='main'?'本题独立代码':'迁移独立代码');editor.autocomplete='off';editor.spellcheck=false;editor.value=session.drafts[which];card.append(editor);
  const checks=el('div','self-check');code.checklist.forEach((text,i)=>{const label=el('label'),input=el('input');input.type='checkbox';input.dataset.selfCheck=`${which}:${i}`;input.checked=!!session.checks[`${which}:${i}`];label.append(input,el('span','',text));checks.append(label)});card.append(el('h3','','自行核对'),checks,el('p','caption','逐项用案例核对代码；这里记录的是自检，不代表程序已自动运行通过。'));panel.append(card);
 }
 function render(){
  panel.replaceChildren();const stage=lesson.stages[session.module];nav.querySelectorAll('button').forEach((b,i)=>{b.classList.toggle('active',i===session.module);b.setAttribute('aria-current',i===session.module?'step':'false')});
  const header=el('div','stage-header');header.append(el('p','eyebrow',`MODULE ${String(session.module+1).padStart(2,'0')}`),el('h2','',stage.title),el('p','',stage.goal));panel.append(header);
  document.querySelector('#frameworkAtlas').hidden=session.module>=4;document.querySelector('#problemDetails').hidden=session.module>=4;
  if(session.module<4){
   const layout=el('div','layout'),left=el('div','visual-column'),right=el('div','questions-column');caseCard(left,session.module===3);const note=el('div','card');note.append(el('h3','','观察与解释'));stage.notes.forEach(n=>note.append(el('p','note',n)));questions(stage.questions,right,`stage:${session.module}`);right.prepend(note);layout.append(left,right);panel.append(layout);
  }else if(session.module===4)codeSlots();
  else{
   const tabs=el('nav','subtabs');tabs.setAttribute('aria-label','独立与迁移');['main','transfer'].forEach((which,i)=>{const b=button(i===0?'独立重写':'迁移任务','subtab',{subtab:which});b.classList.toggle('active',session.subtab===which);tabs.append(b)});panel.append(tabs);
   if(session.subtab==='main')independent('main');else{
    const transfer=lesson.transfer,card=el('div','card');card.append(el('h2','',transfer.title),el('p','',transfer.summary));if(transfer.source){const a=el('a','','查看迁移原题 ↗');a.href=transfer.source;a.target='_blank';a.rel='noreferrer';card.append(a)}panel.append(card);
    const modes=el('nav','subtabs');modes.setAttribute('aria-label','迁移模块');['model','code'].forEach((mode,i)=>{const b=button(i===0?'理解与轨迹':'独立迁移代码','transfer-mode',{mode});b.classList.toggle('active',session.transferMode===mode);modes.append(b)});panel.append(modes);
    if(session.transferMode==='model'){
     const map=el('div','transfer-change');for(const [title,values] of [['保留的思想',transfer.preserved],['改变的规则',transfer.changed]]){const box=el('div');box.append(el('h3','',title),list(values));map.append(box)}card.append(map,el('p','note',`新的证明义务：${transfer.newProof}`));questions(transfer.questions,card,'transfer');caseCard(panel,true,true);
    }else independent('transfer');
   }
  }
 }
 const normalized=code=>code.replace(/("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|\s+/g,(all,quoted)=>quoted||'');
 document.addEventListener('click',event=>{
  const b=event.target.closest('button[data-action]');if(!b)return;
  switch(b.dataset.action){
   case'module':session.module=+b.dataset.module;session.step=0;session.caseId=lesson.stages[session.module].case||lesson.cases[0].id;render();panel.scrollIntoView({block:'start'});break;
   case'subtab':session.subtab=b.dataset.subtab;session.step=0;session.caseId=session.subtab==='transfer'?lesson.transfer.cases[0].id:lesson.cases[0].id;render();break;
   case'transfer-mode':session.transferMode=b.dataset.mode;render();break;
   case'step':session.step+=+b.dataset.delta;render();break;
   case'answer':session.answers[b.dataset.key]={...b._choice,index:+b.dataset.index};render();break;
   case'reference':document.querySelector('#referenceCode').textContent=b.dataset.reference==='main'?lesson.code.reference:lesson.transfer.reference;document.body.classList.add('reference-open');dialog.showModal();break;
   case'close-reference':dialog.close();break;
   case'clear-slots':session.slots={};render();break;
   case'check-slots':{
    let count=0;lesson.code.slots.forEach(slot=>{const value=session.slots[slot.id]||'',ok=!!value.trim()&&slot.accepted.some(answer=>normalized(answer)===normalized(value));const input=panel.querySelector(`[data-slot="${slot.id}"]`);input.classList.toggle('valid',ok);input.classList.toggle('invalid',!ok);if(ok)count++});const feedback=panel.querySelector('#slotFeedback');feedback.className=`feedback ${count===lesson.code.slots.length?'good':'bad'}`;feedback.textContent=count===lesson.code.slots.length?'所有关键表达式与当前契约一致。请进入独立重写。':`${count} / ${lesson.code.slots.length} 个槽位符合契约。复查红色槽位的作用和边界；输入已保留。`;break;
   }
   case'reset':location.reload();break;
  }
 });
 document.addEventListener('input',event=>{if(event.target.dataset.slot)session.slots[event.target.dataset.slot]=event.target.value;if(event.target.dataset.draft)session.drafts[event.target.dataset.draft]=event.target.value});
 document.addEventListener('change',event=>{if(event.target.dataset.action==='case'){session.caseId=event.target.value;session.step=0;render()}if(event.target.dataset.selfCheck)session.checks[event.target.dataset.selfCheck]=event.target.checked});
 document.addEventListener('keydown',event=>{if(event.key==='Tab'&&event.target.matches('textarea.editor')){event.preventDefault();const editor=event.target,start=editor.selectionStart,end=editor.selectionEnd;editor.setRangeText('    ',start,end,'end');session.drafts[editor.dataset.draft]=editor.value}});
 dialog.addEventListener('close',()=>document.body.classList.remove('reference-open'));
 addEventListener('pageshow',event=>{if(event.persisted)location.reload()});
 render();
})();
