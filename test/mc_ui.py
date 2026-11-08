import asyncio, os, sys
from playwright.async_api import async_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL=os.environ.get('URL','http://localhost:8765/')
SHOTS=ROOT+'/test/shots'; os.makedirs(SHOTS, exist_ok=True)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for (w,h,name) in [(1280,900,'desk'),(390,844,'mob')]:
            pg = await b.new_page(viewport={'width':w,'height':h})
            errs=[]; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append(m.type+': '+m.text) if m.type in ('error',) else None)
            await pg.goto(URL); 
            await pg.evaluate('localStorage.clear()'); await pg.reload()
            await pg.wait_for_function("document.querySelectorAll('#grpTable .skel').length===0", timeout=120000)
            print(name,'GROUP:', (await pg.inner_text('#grpTable')).replace('\n',' | ')[:1500])
            await pg.screenshot(path=f'{SHOTS}/mc_{name}_group.png', full_page=True)
            await pg.click('#t-char'); await pg.wait_for_timeout(500)
            await pg.wait_for_function("document.querySelectorAll('#charKpis .skel').length===0", timeout=60000)
            print(name,'CHAR:', (await pg.inner_text('#charKpis')).replace('\n',' | '))
            await pg.screenshot(path=f'{SHOTS}/mc_{name}_char.png', full_page=True)
            if name=='desk':
                await pg.click('#runUps'); await pg.wait_for_function("!document.querySelector('#runUps').disabled", timeout=120000)
                print('UPS:', (await pg.inner_text('#upState')), '|', (await pg.inner_text('#upList')).replace('\n',' | ')[:800])
            print(name,'ERRORS', errs[:5])
            await pg.close()
        await b.close()
asyncio.run(main())
