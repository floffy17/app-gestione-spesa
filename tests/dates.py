"""Visible native date control and backdated transactions on Chromium and WebKit."""
import os
from playwright.sync_api import sync_playwright
URL=os.environ.get('TACCUINO_TEST_URL','http://127.0.0.1:8006/docs/')
with sync_playwright() as p:
    for name in ['chromium','webkit']:
        options={'headless':True}
        if name=='chromium': options.update(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        try: browser=getattr(p,name).launch(**options)
        except Exception as e:
            if name=='webkit': print('WEBKIT UNRUN:',str(e).splitlines()[0]);continue
            raise
        context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(URL);page.wait_for_function('window.__taccuino')
        page.locator('[data-act="new-exp"]').click()
        page.locator('#f-amt').fill('25,50');page.locator('#f-text').fill('Spesa retrodatata')
        date=page.locator('#f-date-in');assert date.is_visible()
        assert date.get_attribute('aria-hidden') is None and date.get_attribute('tabindex') is None
        assert date.bounding_box()['height']>=48
        # Click stays on the real input, without a delegated action cancelling native behavior.
        assert date.evaluate('(el)=>!el.closest("[data-act]")')
        date.click();date.fill('2025-02-14');date.dispatch_event('change')
        page.locator('#f-save').click()
        assert page.evaluate('__taccuino.S().mov[0].d')=='2025-02-14'
        assert page.evaluate('__taccuino.monthStats("2025-02").out')==2550
        page.locator('[data-act="edit-mov"]').click()
        assert page.locator('#f-date-in').input_value()=='2025-02-14'
        page.locator('#f-date-in').fill('2024-12-31');page.locator('#f-save').click()
        assert page.evaluate('__taccuino.monthStats("2025-02").out')==0
        assert page.evaluate('__taccuino.monthStats("2024-12").out')==2550
        page.locator('[data-act="new-exp"]').click();page.locator('#f-amt').fill('3')
        page.locator('#f-date-in').fill('');assert page.locator('#f-save').is_disabled()
        page.locator('[data-act="date"]').filter(has_text='Ieri').click()
        assert page.locator('#f-save').is_enabled();page.locator('#f-save').click()
        page.locator('[data-act="new-inc"]').click();page.locator('#f-amt').fill('100')
        page.locator('#f-date-in').fill('2024-12-31');page.locator('#f-save').click()
        assert page.evaluate('__taccuino.monthStats("2024-12").inc')==10000
        page.locator('[data-act="new-exp"]').click();page.locator('#f-amt').fill('5');page.locator('#f-text').fill('Spesa futura')
        page.locator('#f-date-in').fill('2030-08-15');page.locator('#f-save').click()
        assert page.evaluate('__taccuino.monthStats("2030-08").out')==500
        page.locator('#nav-prom').click();page.locator('[data-act="new-dia"]').click()
        page.locator('#f-text').fill('Attività in altra data');page.locator('#f-date-in').fill('2026-01-02');page.locator('#f-save').click()
        page.reload();page.wait_for_function('window.__taccuino')
        assert page.evaluate('__taccuino.S().dia[0].d')=='2026-01-02'
        assert page.evaluate('__taccuino.S().mov[0].d')=='2024-12-31'
        assert not errors,errors
        print('PASS',name,': visible accessible date field; past date, edit, monthly totals, empty date validation, Yesterday shortcut, income, diary and reload persistence')
        context.close();browser.close()
