import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const root=new URL('./dist/',import.meta.url);
const read=name=>readFileSync(new URL(name,root),'utf8');
const source=read('i18n.js');
const start=source.indexOf('const translations = ')+21;
const end=source.indexOf('\n  };',start)+4;
const translations=vm.runInNewContext('('+source.slice(start,end)+')');
const keys=Object.keys(translations.zh);
for(const language of ['en','ja']) {
  for(const key of keys) assert.ok(translations[language][key]?.trim(),`${language}: ${key}`);
  assert.equal(Object.keys(translations[language]).length,keys.length);
}
for(const name of ['index.html','guide.html']) {
  const html=read(name);
  assert.equal((html.match(/data-language-select/g)||[]).length,1,name);
  assert.doesNotMatch(html,/data-language-toggle|data-original-language|original-languages/);
  assert.match(html,/<select class="language"[^>]*>[\s\S]*?value="zh"[\s\S]*?value="en"[\s\S]*?value="ja"[\s\S]*?<\/select>/);
  for(const [,key] of html.matchAll(/data-i18n(?:-html|-placeholder|-aria-label)?="([^"]+)"/g)) for(const language of ['zh','en','ja']) assert.ok(translations[language][key],`${name} ${language}: ${key}`);
  for(const [,ref] of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
    if(/^(https?:|#)/.test(ref))continue;
    readFileSync(new URL(ref,root));
  }
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]); assert.equal(ids.length,new Set(ids).size);
}
assert.match(read('index.html'),/id="credits"/);
assert.match(read('index.html'),/G-MKGQEE5V97/);
assert.match(read('index.html'),/data-release-pending="v1\.1\.0"/);
for (const version of ['v1.0.5','v1.1.0','v1.1.1','v1.2.0']) {
  const pendingNode={dataset:{releasePending:'v1.1.0'},hidden:false};
  const versionNode={textContent:''};
  const document={querySelectorAll:selector=>selector==='[data-release-pending]'?[pendingNode]:selector==='[data-version]'?[versionNode]:[]};
  vm.runInNewContext(read('site.js'),{document,window:{MANAKA_DOWNLOADS:{version}}});
  assert.equal(pendingNode.hidden,version!=='v1.0.5');
  assert.equal(versionNode.textContent,version);
}
for (const githubUrl of ['', 'https://example.com/release.zip']) {
  const node={dataset:{channelPending:'github'},hidden:false};
  vm.runInNewContext(read('site.js'),{document:{querySelectorAll:selector=>selector==='[data-channel-pending]'?[node]:[]},window:{MANAKA_DOWNLOADS:{githubUrl}}});
  assert.equal(node.hidden,Boolean(githubUrl));
}
for(const file of ['QUICKSTART_JA.md','FAQ_JA.md']) {
  const text=read(file);assert.ok(text.length>1500,file);assert.match(text,/ゲーム本体.*含まれ/);assert.match(text,/v1\.1\.3/);assert.match(text,/一時停止/);
}

function fixture(url,saved) {
  const values=new Map(saved?[['manaka-site-language',saved]]:[]),listeners={};
  const select={value:'',addEventListener(key,fn){this[key]=fn;}};
  const link={href:'guide.html#setup',getAttribute(){return this.href;}};
  const nodes=keys.map(key=>({dataset:{i18n:key},textContent:''}));
  const panels=['zh','en','ja'].map(language=>({id:'original-'+language,lang:language,dataset:{originalTitle:language}}));
  const heading={},section={querySelectorAll:()=>panels,querySelector:()=>heading};
  const document={body:{classList:{contains:()=>false}},documentElement:{lang:'zh-CN'},querySelectorAll(selector){if(selector==='[data-language-select]')return[select];if(selector==='[data-language-link]')return[link];if(selector==='[data-i18n]')return nodes;return[];},querySelector(selector){return selector==='#original-work'?section:null;}};
  const window={location:{href:url,search:new URL(url).search},history:{replaceState(_a,_b,path){window.location.href=new URL(path,window.location.href).href;}},addEventListener(key,fn){(listeners[key]??=[]).push(fn);},dispatchEvent(event){for(const fn of listeners[event.type]||[])fn(event);}};
  const context=vm.createContext({document,window,URL,URLSearchParams,localStorage:{getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)},CustomEvent:class {constructor(type,options){this.type=type;this.detail=options.detail;}}});
  vm.runInContext(source,context);vm.runInContext(read('original-work.js'),context);
  return{window,document,values,select,link,heading,panels};
}
for(const language of ['zh','en','ja']) {
  const f=fixture(`https://example.com/?lang=${language}`,'en');
  assert.equal(f.window.ManakaI18n.language,language);
  f.select.value=language;f.select.change();
  assert.equal(f.select.value,language);assert.equal(f.heading.textContent,language);
  assert.equal(f.panels.filter(panel=>!panel.hidden).length,1);
  assert.equal(new URL(f.link.href,'https://example.com').searchParams.get('lang'),language);
  assert.ok(f.link.href.endsWith('#setup'));
  assert.equal(f.values.get('manaka-site-language'),language);
  assert.ok(!f.window.ManakaI18n.t('guide.source',{file:'QUICKSTART_JA.md'}).includes('{file}'));
}
assert.equal(fixture('https://example.com/guide.html','ja').window.ManakaI18n.language,'ja');
assert.equal(fixture('https://example.com/?lang=invalid','ja').window.ManakaI18n.language,'ja');

// Fast language changes must not allow a stale fetch to replace the selected document.
const pending=[],handlers={};
const makeNode=()=>({dataset:{},classList:{contains:()=>false,toggle(){}},addEventListener(key,fn){this[key]=fn;},querySelectorAll:()=>[],replaceChildren(){this.innerHTML='';},append(){}});
const elements=Object.fromEntries(['docContent','docToc','docSource','rawDocLink','docError','docSearch','searchStatus'].map(id=>[id,makeNode()]));
const tabs=['quickstart','faq'].map(kind=>({...makeNode(),dataset:{docKind:kind}}));
tabs[0].classList.contains=()=>true;
const guideWindow={ManakaI18n:{language:'ja',t:key=>key},addEventListener(key,fn){handlers[key]=fn;}};
vm.runInNewContext(read('markdown-guide.js'),{document:{querySelector:s=>elements[s.slice(1)],querySelectorAll:()=>tabs},window:guideWindow,fetch:file=>new Promise(resolve=>pending.push({file,resolve})),console});
assert.equal(pending[0].file,'QUICKSTART_JA.md');
guideWindow.ManakaI18n.language='en';handlers['manaka:languagechange']();
assert.equal(pending[1].file,'QUICKSTART_EN.md');
pending[1].resolve({ok:true,text:async()=> '# English current'});await new Promise(resolve=>setImmediate(resolve));
pending[0].resolve({ok:true,text:async()=> '# Japanese stale'});await new Promise(resolve=>setImmediate(resolve));
assert.match(elements.docContent.innerHTML,/English current/);assert.doesNotMatch(elements.docContent.innerHTML,/Japanese stale/);
guideWindow.ManakaI18n.language='ja';tabs[1].click();assert.equal(pending[2].file,'FAQ_JA.md');
console.log(`Manaka website checks passed: ${keys.length} keys in 3 languages, unified dropdowns, persisted locale, attribution, Japanese guide/FAQ and stale-fetch protection.`);
