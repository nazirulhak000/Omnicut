"""Render clicks keep Cutout enabled; only the explicit fallback disables it.

Production EditorShell/RenderButton, synthetic temp media and in-memory API.
No render worker, model or real project/export storage is used.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.clip_pair import create_clip_source
from tests.motion_capture.overlay_pair import vite_fs_url


@pytest.mark.parametrize('cutout_enabled', [True, False, None])
def test_render_click_preserves_cutout_and_explicit_fallback_disables(motion_fixture_url, cutout_enabled):
    parsed = urlsplit(motion_fixture_url)
    base_url = f'{parsed.scheme}://{parsed.netloc}'
    with temp_capture_dir('render-cutout-click-') as temp_root:
        source = create_clip_source(Path(temp_root))
        clip_url = vite_fs_url(base_url, source)
        manifest = {
            'project_name': 'editor-audit',
            'clip_list': [{'source_path': clip_url, 'trim_start': 0, 'trim_end': 2, 'duration': 2}],
            'transitions': [], 'cues': [], 'artifacts': {}, 'show_watermark': False,
        }
        if cutout_enabled is not None:
            manifest['background_isolation'] = {
                'schema_version': 1, 'enabled': cutout_enabled,
                'scope_mode': 'behind_text_windows',
            }
        requests = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={'width': 1600, 'height': 1100}, ignore_https_errors=True)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))

                def mock_api(route):
                    request = route.request
                    path = urlsplit(request.url).path
                    status = 200
                    if path == '/api/projects/editor-audit' and request.method == 'GET':
                        response = manifest
                    elif path == '/api/projects/editor-audit/state' and request.method == 'PATCH':
                        manifest.update(request.post_data_json or {})
                        response = manifest
                    elif path == '/api/projects':
                        response = {'projects': ['editor-audit']}
                    elif path == '/api/products':
                        response = {'products': [{'id': 'test-product', 'angles': [{
                            'angle_id': 'test-angle', 'project_name': 'editor-audit',
                            'status': 'in_production', 'cover_path': 'test-cover-metadata-only.webp',
                        }]}]}
                    elif path == '/api/assets/all':
                        response = {'sfx': [], 'music': [], 'fonts': [], 'stickers': [], 'luts': [], 'effects': []}
                    elif path == '/api/hook-motion-presets':
                        response = {'catalog': {}, 'default': None}
                    elif path == '/api/reroll' and request.method == 'POST':
                        requests.append(request.post_data_json)
                        # Exercise the explicit fallback without starting a real job.
                        status, response = 409, {'detail': 'Cutout test render rejected'}
                    else:
                        response = {'tasks': [], 'milestones': [], 'custom': []}
                    route.fulfill(status=status, content_type='application/json', body=json.dumps(response))

                page.route('**/api/**', mock_api)
                page.goto(f'{base_url}/editor_shell_audit.html?clip={clip_url}&renderAudit=1',
                          wait_until='domcontentloaded')
                page.locator('[data-timeline-item="clip"]:visible').first.wait_for(timeout=15000)
                render = page.get_by_role('button', name='เรนเดอร์', exact=True)
                render.wait_for(timeout=10000)
                with page.expect_response(lambda res: urlsplit(res.url).path == '/api/reroll'
                                          and res.request.method == 'POST'):
                    render.click()
                assert len(requests) == 1
                cfg = requests[0].get('background_isolation')
                if cutout_enabled is None:
                    assert cfg is None
                else:
                    assert cfg['enabled'] is cutout_enabled, requests[0]
                assert not page.get_by_text('เริ่มเรนเดอร์แบบไม่ใช้ Cutout ชั่วคราว...', exact=True).count()
                fallback = page.get_by_role('button', name='เรนเดอร์แบบไม่ใช้ Cutout', exact=True)
                with page.expect_response(lambda res: urlsplit(res.url).path == '/api/reroll'
                                          and res.request.method == 'POST'):
                    fallback.click()
                assert len(requests) == 2
                assert requests[1]['background_isolation']['enabled'] is False
                assert not errors, errors
            finally:
                browser.close()
