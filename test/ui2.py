import asyncio
from playwright.async_api import async_playwright
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL='file://'+ROOT+'/local/site/shaman/index.html'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await b.new_page(viewport={'width':1280,'height':900})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL+'#upgrades'); await pg.wait_for_timeout(1500)
        print('UPS L8 best:', (await pg.inner_text('#bestUps')).replace('\n',' | ')[:2500])
        print('SLOT:', (await pg.inner_text('#slotUps')).replace('\n',' | ')[:1500])
        print('ERR', errs)
        await b.close()
asyncio.run(main())
