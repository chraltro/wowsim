import asyncio, sys
from playwright.async_api import async_playwright
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL='file://'+ROOT+'/dist/shaman/index.html'
os.makedirs(ROOT+'/test/shots', exist_ok=True)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for (w,h,name) in [(1280,900,'desk'),(390,844,'mob')]:
            pg = await b.new_page(viewport={'width':w,'height':h})
            errs=[]
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append('console '+m.type+': '+m.text) if m.type in ('error','warning') else None)
            await pg.goto(URL)
            await pg.wait_for_timeout(800)
            await pg.screenshot(path=f'{ROOT}/test/shots/{name}_l8_top.png', full_page=False)
            await pg.screenshot(path=f'{ROOT}/test/shots/{name}_l8_full.png', full_page=True)
            txt = await pg.inner_text('#questOut')
            print(name, 'QUEST L8:', txt[:900].replace('\n',' | '))
            print(name, 'UNLOCKS:', (await pg.inner_text('#lvUnlocks')).replace('\n',' | '))
            print(name, 'ROUTES:', (await pg.inner_text('#routes')).replace('\n',' | ')[:600])
            # run dungeon sim at level 8
            await pg.click('#run'); await pg.wait_for_selector('#results .kpi', timeout=60000)
            print(name, 'DUNG L8:', (await pg.inner_text('#results')).replace('\n',' | ')[:500])
            for L in [20, 40, 60]:
                await pg.fill('#level', str(L)); await pg.dispatch_event('#level','change'); await pg.wait_for_timeout(300)
                print(name, 'QUEST L%d:'%L, (await pg.inner_text('#questOut')).replace('\n',' | ')[:400])
                await pg.click('#run'); await pg.wait_for_selector('#results .kpi', timeout=90000)
                print(name, 'DUNG L%d:'%L, (await pg.inner_text('#results .kpis')).replace('\n',' | ')[:300])
            await pg.screenshot(path=f'{ROOT}/test/shots/{name}_l60_full.png', full_page=True)
            await pg.fill('#level', '8'); await pg.dispatch_event('#level','change'); await pg.wait_for_timeout(200)
            await pg.click('#t-up'); await pg.wait_for_timeout(1500)
            print(name, 'UPS L8:', (await pg.inner_text('#bestUps')).replace('\n',' | ')[:1500])
            await pg.screenshot(path=f'{ROOT}/test/shots/{name}_ups_l8.png', full_page=True)
            print(name, 'ERRORS', errs)
            await pg.close()
        await b.close()
asyncio.run(main())
