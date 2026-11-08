import asyncio
from playwright.async_api import async_playwright
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL='file://'+ROOT+'/dist/shaman/index.html'
os.makedirs(ROOT+'/test/shots', exist_ok=True)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for (w,h,name) in [(1280,1000,'desk'),(390,844,'mob')]:
            pg = await b.new_page(viewport={'width':w,'height':h}, device_scale_factor=1)
            await pg.goto(URL); await pg.wait_for_timeout(900)
            await pg.screenshot(path=f'{ROOT}/test/shots/{name}_a.png', full_page=False)
            el = await pg.query_selector('#v-simulate')
            await el.screenshot(path=f'{ROOT}/test/shots/{name}_quest.png')
            await pg.close()
        await b.close()
asyncio.run(main())
