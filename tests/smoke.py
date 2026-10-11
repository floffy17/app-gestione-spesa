"""Run with python3 tests/smoke.py against npm run dev (port 8001)."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get('TACCUINO_TEST_URL', 'http://127.0.0.1:8001')

def budget(page, scope, amount):
    if scope != 'total':
        page.locator('.category-budgets').evaluate('(el) => el.open = true')
    page.locator(f'[data-act="budget-edit"][data-scope="{scope}"]').click()
    page.locator('#f-amt').fill(amount)
    page.locator('#f-save').click()

def movement(page, amount, text, income=False):
    page.locator('[data-act="new-inc"]' if income else '[data-act="new-exp"]').click()
    page.locator('#f-amt').fill(amount)
    page.locator('#f-text').fill(text)
    page.locator('#f-save').click()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), args=['--no-sandbox'])
    context = browser.new_context(viewport={'width':390, 'height':844}, reduced_motion='reduce')
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL)
    page.wait_for_function('window.__taccuino')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    for text in ['Spesa Lidl', 'Pizza Conad', 'Supermercato', 'Spesa alimentare', 'Esselunga']:
        assert page.evaluate('(text) => __taccuino.suggestCat(text)', text) == 'supermercato'
    assert page.evaluate('__taccuino.suggestCat("Pizza")') == 'svago'
    assert page.evaluate('__taccuino.suggestCat("Felpa")') == 'utilita'
    # Mock the native adapter at the platform boundary; exercises real permission and dedup logic.
    page.evaluate('''() => {
        window.sent = [];
        window.TaccuinoNative = {isNative: () => true, requestPermission: async () => true,
            notify: async (body, scope) => window.sent.push({body, scope})};
    }''')
    budget(page, 'total', '100')
    budget(page, 'supermercato', '50')
    page.locator('[data-act="notifications"]').click()
    page.wait_for_function('__taccuino.S().budget.notifications')
    movement(page, '40', 'Spesa Lidl')
    assert page.evaluate('__taccuino.budgetState("supermercato").stage') == 80
    assert page.evaluate('sent.length') == 1
    movement(page, '10', 'Spesa Conad')
    assert page.evaluate('__taccuino.budgetState("supermercato").stage') == 100
    assert page.evaluate('sent.length') == 2
    movement(page, '30', 'Pizza')
    assert page.evaluate('__taccuino.budgetState().stage') == 80
    movement(page, '1000', 'Stipendio', income=True)
    assert page.evaluate('__taccuino.budgetState().spent') == 8000
    assert page.evaluate('sent.length') == 3  # income must not repeat a threshold alert
    page.locator('[data-act="sub"][data-sub="mesi"]').click()
    page.locator('[data-act="new-fix"]').click()
    page.locator('#f-text').fill('Telefono'); page.locator('#f-amt').fill('20'); page.locator('#f-save').click()
    assert page.evaluate('__taccuino.budgetState().spent') == 10000
    assert page.evaluate('__taccuino.budgetState().stage') == 100
    assert page.evaluate('sent.length') == 4
    page.locator('[data-act="sub"][data-sub="giorni"]').click()
    # Manual choice overrides auto classification and is learned for later entries.
    page.locator('[data-act="new-exp"]').click()
    page.locator('#f-amt').fill('1');page.locator('#f-text').fill('Lidl regalo')
    page.locator('[data-act="cat"][data-cat="utilita"]').click();page.locator('#f-save').click()
    assert page.evaluate('__taccuino.suggestCat("Lidl regalo")') == 'utilita'
    page.reload();page.wait_for_function('window.__taccuino')
    assert page.evaluate('__taccuino.S().budget.limit') == 10000
    assert page.evaluate('__taccuino.S().budget.categories.supermercato') == 5000
    assert page.evaluate('__taccuino.monthStats(new Date().getFullYear()+"-"+String(new Date().getMonth()+1).padStart(2,"0")).cats.supermercato') == 5000
    assert page.locator('[data-budget-scope="total"] .budget-alert').count() == 1
    # Negative/zero amounts cannot create limits.
    page.locator('[data-act="budget-edit"][data-scope="total"]').click()
    page.locator('#f-amt').fill('0');assert page.locator('#f-save').is_disabled()
    page.locator('[data-act="budget-remove"]').click()
    assert page.evaluate('__taccuino.S().budget.limit') == 0
    assert page.evaluate('__taccuino.S().budget.categories.supermercato') == 5000
    # Offline app shell and local data after service worker activation.
    page.wait_for_function('navigator.serviceWorker.controller !== null')
    context.set_offline(True);page.reload();page.wait_for_function('window.__taccuino')
    assert page.evaluate('__taccuino.S().mov.length') == 5
    movement(page, '2', 'Caffè offline')
    page.reload();page.wait_for_function('window.__taccuino')
    assert page.evaluate('__taccuino.S().mov.some(x => x.t === "Caffè offline")')
    context.set_offline(False)
    assert not errors, errors
    print('PASS: classification, manual overrides, monthly/category budgets, 80/100% thresholds, notification dedup, income exclusion, fixed costs, persistence, removal, offline use, mobile layout')
    context.close()
    # Migration from the uploaded version preserves transactions and learns.
    old = browser.new_context()
    old.add_init_script('''localStorage.setItem('taccuino.data', JSON.stringify({v:1,mov:[{id:'old',d:'2026-10-01',a:100,c:'altro',t:'Vecchia spesa',ts:1}],fix:[],dia:[],todo:[],learn:{pizza:'svago'},ui:{}}));''')
    migrated = old.new_page(); migrated.goto(URL);migrated.wait_for_function('window.__taccuino')
    assert migrated.evaluate('__taccuino.S().mov[0].c') == 'svago'
    assert migrated.evaluate('__taccuino.S().mov[0].a') == 100
    assert migrated.evaluate('__taccuino.S().budget.limit') == 0
    print('PASS: legacy data migration')
    old.close()
    # Denied notification permission leaves in-app warnings usable.
    denied = browser.new_context()
    denied_page = denied.new_page(); denied_page.goto(URL); denied_page.wait_for_function('window.__taccuino')
    denied_page.evaluate("window.TaccuinoNative = {isNative: () => true, requestPermission: async () => false};")
    denied_page.locator('[data-act="notifications"]').click()
    denied_page.wait_for_function('document.querySelector("#notification-status").textContent.includes("Permesso non concesso")')
    assert denied_page.evaluate('__taccuino.S().budget.notifications') is False
    budget(denied_page, 'total', '10'); movement(denied_page, '10', 'Pizza')
    assert denied_page.locator('.budget-alert').count() == 1
    # Month rollover resets usage without discarding configured recurring limits.
    denied_page.clock.set_fixed_time('2026-12-15T12:00:00Z')
    denied_page.evaluate('document.dispatchEvent(new Event("visibilitychange"))')
    assert denied_page.evaluate('__taccuino.budgetState().spent') == 0
    assert denied_page.evaluate('__taccuino.budgetState().limit') == 1000
    assert denied_page.locator('.budget-alert').count() == 0
    print('PASS: denied notifications fallback and monthly rollover')
    denied.close();browser.close()
