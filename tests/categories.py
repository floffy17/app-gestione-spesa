"""Category editing and same-origin upgrade preserve existing data."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json, shutil, subprocess, tempfile, threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = 'ab907b5502d51e315d81d8422671ac065bf40d5e'
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        # Local copy timestamps are unrelated to deployed content; always serve the current file.
        if 'If-Modified-Since' in self.headers: del self.headers['If-Modified-Since']
        super().do_GET()

def manager(page):
    page.locator('.category-manager').evaluate('(el) => el.open = true')

def edit(page, id, name, color, limit):
    manager(page)
    page.locator(f'[data-act="category-edit"][data-id="{id}"]').click()
    page.locator('#f-text').fill(name)
    page.locator('#f-color').fill(color)
    page.locator('#f-amt').fill(limit)
    page.locator('#f-save').click()

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp); site = root/'app-gestione-spesa'; site.mkdir()
    # Initially serve the exact previous published version, including its service worker.
    for path in subprocess.check_output(['git','ls-tree','-r','--name-only',PREVIOUS,'docs'],cwd=ROOT,text=True).splitlines():
        target = site/Path(path).relative_to('docs');target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(subprocess.check_output(['git','show',PREVIOUS+':'+path],cwd=ROOT))
    server = ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=root))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/app-gestione-spesa/'
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
        page=context.new_page(); errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
        page.goto(url);page.wait_for_function('window.__taccuino')
        date=page.evaluate('new Date().getFullYear()+"-"+String(new Date().getMonth()+1).padStart(2,"0")+"-01"')
        fixture={'v':1,'mov':[{'id':'old1','d':date,'a':3000,'c':'svago','t':'Pizza','ts':1}, {'id':'old2','d':date,'a':1500,'c':'supermercato','t':'Conad','ts':2}], 'fix':[{'id':'fixed','n':'Telefono','s':date[:7],'e':None,'h':[{'m':date[:7],'a':1000}]}], 'dia':[{'id':'note','d':date,'t':'Nota da conservare','ts':1}], 'todo':[{'id':'todo','t':'Attività precedente','done':False,'ts':1}], 'learn':{'pizza':'svago'},'ui':{'tab':'costi'}, 'budget':{'limit':50000,'categories':{'svago':20000,'supermercato':10000},'notices':{},'notifications':False}}
        page.evaluate('(data) => localStorage.setItem("taccuino.data", JSON.stringify(data))',fixture)
        page.reload();page.wait_for_function('window.__taccuino');assert page.evaluate('__taccuino.version')=='1.2'
        page.wait_for_function('navigator.serviceWorker.controller !== null')
        # Replace the files exactly as a Pages deployment would; origin and storage remain unchanged.
        shutil.copytree(ROOT/'docs',site,dirs_exist_ok=True)
        page.reload();page.wait_for_function('__taccuino.version === "1.3.1"')
        state=page.evaluate('__taccuino.S()')
        for key in ['mov','fix','dia','todo','learn','ui']:assert state[key]==fixture[key],key
        assert state['budget']['limit']==50000 and state['budget']['categories']['svago']==20000
        edit(page,'svago','Tempo libero','#9b4dca','200')
        assert page.evaluate('__taccuino.S().mov[0].c')=='svago'
        assert page.locator('[data-act="drill"][data-cat="svago"] .dot').evaluate('(el)=>el.style.background')=='rgb(155, 77, 202)'
        manager(page);page.locator('[data-act="category-new"]').click()
        page.locator('#f-text').fill('Animali');page.locator('#f-color').fill('#008b8b');page.locator('#f-amt').fill('50');page.locator('#f-save').click()
        custom=page.evaluate('__taccuino.S().categories.find(c=>c.name==="Animali").id')
        assert page.evaluate('(id)=>__taccuino.S().budget.categories[id]',custom)==5000
        page.evaluate('window.sent=[];window.TaccuinoNative={isNative:()=>true,notify:async (body,scope)=>sent.push({body,scope})};__taccuino.S().budget.notifications=true')
        page.locator('[data-act="new-exp"]').click();page.locator('#f-amt').fill('40');page.locator('#f-text').fill('Veterinario');page.locator(f'[data-act="cat"][data-cat="{custom}"]').click();page.locator('#f-save').click()
        assert page.evaluate('(id)=>__taccuino.budgetState(id).stage',custom)==80
        assert page.evaluate('(id)=>sent.some(x=>x.scope===id)',custom)
        assert page.evaluate('__taccuino.suggestCat("Veterinario")')==custom
        assert page.locator(f'[data-act="drill"][data-cat="{custom}"] .dot').evaluate('(el)=>el.style.background')=='rgb(0, 139, 139)'
        assert page.locator(f'#pager svg [data-cat="{custom}"]').count()==1
        edit(page,custom,'Cura animali','#e34948','60')
        assert page.evaluate('(id)=>__taccuino.S().mov[2].c===id',custom)
        # Duplicate names and invalid budgets must not save.
        manager(page);page.locator('[data-act="category-new"]').click();page.locator('#f-text').fill('cura ANIMALI')
        assert page.locator('#f-save').is_disabled()
        page.locator('#f-text').fill('Viaggi');page.locator('#f-amt').fill('-10');assert page.locator('#f-save').is_disabled()
        page.locator('#f-amt').fill('');assert page.locator('#f-save').is_enabled();page.locator('#f-save').click()
        edit(page,'utilita','<b>Casa</b>','#eda100','0')
        assert page.locator('[data-act="drill"][data-cat="utilita"] .txt').inner_text().startswith('<b>Casa</b>')
        assert page.locator('[data-act="drill"][data-cat="utilita"] .txt b').count()==0
        page.reload();page.wait_for_function('__taccuino.version === "1.3.1"')
        state=page.evaluate('__taccuino.S()')
        assert len(state['mov'])==3 and state['mov'][:2]==fixture['mov']
        assert state['dia']==fixture['dia'] and state['todo']==fixture['todo'] and state['fix']==fixture['fix']
        assert state['budget']['limit']==50000 and state['budget']['categories'][custom]==6000
        assert page.evaluate('__taccuino.suggestCat("Veterinario")')==custom
        assert page.evaluate('(id)=>__taccuino.budgetState(id).spent',custom)==4000
        page.wait_for_function('navigator.serviceWorker.controller !== null')
        page.evaluate('navigator.serviceWorker.getRegistration().then(r=>r.update())')
        page.wait_for_function('caches.keys().then(keys=>keys.includes("taccuino-v1.3.1"))')
        context.set_offline(True);page.reload();page.wait_for_function('__taccuino.version === "1.3.1"')
        assert page.evaluate('__taccuino.S().mov.length')==3
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors,errors
        print('PASS: same-origin 1.2→1.3 upgrade with service worker preserves transactions, fixed costs, diary, tasks, learned categories and budgets; custom categories, rename, colors, limits, alerts, duplicate validation, safe names, reload and offline persistence')
        context.close();browser.close()
    server.shutdown()
