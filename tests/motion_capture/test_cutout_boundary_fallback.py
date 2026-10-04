"""Canvas cut-boundary fallback obeys transition alpha and footage geometry."""
from urllib.parse import urlsplit
from pathlib import Path
from playwright.sync_api import sync_playwright
from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.clip_pair import create_clip_source
from tests.motion_capture.overlay_pair import vite_fs_url


def test_waiting_cutout_keeps_footage_with_same_transition_geometry(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    base = f'{parsed.scheme}://{parsed.netloc}'
    with temp_capture_dir('cutout-boundary-') as root:
        source = create_clip_source(Path(root))
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page(ignore_https_errors=True)
                page.goto(f'{base}/editor_controls.html')
                result = page.evaluate("""async url => {
                  const {drawClipInto} = await import('/src/components/SequencePlayer.jsx');
                  const video=document.createElement('video');video.muted=true;
                  await new Promise((resolve,reject)=>{video.onloadeddata=resolve;video.onerror=reject;video.src=url;});
                  const make=()=>{const c=document.createElement('canvas');c.width=540;c.height=960;return c;};
                  const differences=[];
                  for (const clip of [{},{zoom:1.3,pan_x:.25,mirror:true},{rotation:90}]) {
                    for (const alpha of [.25,.5,1]) {
                      const expected=make(),actual=make();
                      // Single footage pass, as used by the transition fallback.
                      drawClipInto(expected.getContext('2d'),video,clip,alpha,0,null,'footage');
                      drawClipInto(actual.getContext('2d'),video,clip,alpha,0,{pendingCutout:true,decoderWaiting:true});
                      const e=expected.getContext('2d').getImageData(0,0,540,960).data;
                      const a=actual.getContext('2d').getImageData(0,0,540,960).data;
                      differences.push(a.reduce((sum,v,i)=>sum+(v!==e[i]),0));
                    }
                  }
                  const missing=make();
                  drawClipInto(missing.getContext('2d'),video,{},1,0,{pendingCutout:true});
                  const p=Array.from(missing.getContext('2d').getImageData(270,480,1,1).data);
                  video.removeAttribute('src');video.load();
                  return {differences,missing:p};
                }""", vite_fs_url(base, source))
                assert result['differences'] == [0] * 9
                assert result['missing'] == [11, 18, 32, 255]
            finally:
                browser.close()
