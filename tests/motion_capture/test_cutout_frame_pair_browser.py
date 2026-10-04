"""Real Canvas pixels: source RGB, alpha occlusion and complete-pair holding."""
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def test_cutout_pair_uses_source_pixels_and_holds_both_layers(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(ignore_https_errors=True)
            page.goto(f'{parsed.scheme}://{parsed.netloc}/editor_controls.html')
            result = page.evaluate("""async () => {
              const {createCutoutFramePair} = await import('/src/lib/cutoutFramePair.js');
              const make = () => {const c = document.createElement('canvas'); c.width=64; c.height=64; return c;};
              const source = make(), mask = make(), out = make();
              source.videoWidth=64; source.videoHeight=64; source.readyState=4; mask.readyState=4;
              source.getContext('2d').fillStyle='blue'; source.getContext('2d').fillRect(0,0,64,64);
              const mc = mask.getContext('2d'); mc.fillStyle='red'; mc.fillRect(32,0,32,64);
              const frames=createCutoutFramePair();
              const args={source,mask,sourceTime:8,maskTime:0,sourceStart:8,fps:30,requestedTime:8,artifactKey:'a'};
              const subject=frames.resolve(args);
              const ctx=out.getContext('2d');
              const paint = s => {ctx.clearRect(0,0,64,64);ctx.drawImage(s._cutoutSourceFrame,0,0);
                ctx.fillStyle='yellow';ctx.fillRect(0,0,64,64);ctx.drawImage(s,0,0);};
              paint(subject);
              const px=x=>Array.from(ctx.getImageData(x,32,1,1).data);
              const left=px(10),right=px(50);
              source.getContext('2d').fillStyle='green';source.getContext('2d').fillRect(0,0,64,64);
              const held=frames.resolve({...args,sourceTime:8.1,requestedTime:8.1});
              const heldRGB=Array.from(held._cutoutSourceFrame.getContext('2d').getImageData(50,32,1,1).data);
              paint(held);
              return {left,right,heldRGB,heldRight:px(50),same:held===subject,
                seekCleared:frames.resolve({...args,sourceTime:12,requestedTime:12})===null};
            }""")
            assert result['left'] == [255, 255, 0, 255]  # Hook visible through alpha.
            assert result['right'] == [0, 0, 255, 255]  # Source blue, never artifact red.
            assert result['heldRGB'] == result['heldRight'] == [0, 0, 255, 255]
            assert result['same'] and result['seekCleared']
        finally:
            browser.close()
