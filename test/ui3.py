import asyncio
from playwright.async_api import async_playwright
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL='file://'+ROOT+'/dist/index.html'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await b.new_page(viewport={'width':1280,'height':900})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(800)
        await pg.click('#f-gear summary'); await pg.click('[data-pick="mainhand"]'); await pg.wait_for_timeout(800)
        print('PICK:', (await pg.inner_text('#pickNote')), '|', (await pg.inner_text('#pickList')).replace('\n',' | ')[:500])
        await pg.fill('#pickSearch','Icepane'); await pg.wait_for_timeout(200)
        await pg.click('.pick'); await pg.wait_for_timeout(500)
        print('GEAR:', (await pg.inner_text('#sum-gear')))
        print('QUEST:', (await pg.inner_text('#questOut .kpis')).replace('\n',' | '))
        print('TABLE:', (await pg.inner_text('#questOut table')).replace('\n',' | '))
        # level 10 talents
        await pg.click('#lvUp'); await pg.click('#lvUp'); await pg.wait_for_timeout(300)
        print('L10 ROUTES:', (await pg.inner_text('#routes')).replace('\n',' | '))
        print('L10 QUEST:', (await pg.inner_text('#questOut .kpis')).replace('\n',' | '))
        # combat log
        await pg.click('#t-log'); await pg.set_input_files('#logFile', 'test/sample.txt'); await pg.wait_for_selector('#logOut .kpi', timeout=30000)
        print('LOG:', (await pg.inner_text('#logOut .kpis')).replace('\n',' | '))
        # high-level gear warning
        await pg.click('#t-sim'); await pg.select_option('#preset', 'resto_timesaver'); await pg.wait_for_timeout(400)
        print('WARN:', await pg.inner_text('#gearWarn'), '|', await pg.inner_text('#sum-gear'))
        print('ERR', errs)
        await b.close()
asyncio.run(main())
