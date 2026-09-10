import pytest
from scripts.api_server import app

EXPECTED_API_ROUTES = {
    ("POST", "/api/ai/parse"),
    ("POST", "/api/ai/prompt"),
    ("GET", "/api/ai/status"),
    ("GET", "/api/angles"),
    ("GET", "/api/assets/all"),
    ("POST", "/api/assets/rescan"),
    ("POST", "/api/assets/upload"),
    ("POST", "/api/delete-file"),
    ("GET", "/api/editor/filmstrip"),
    ("GET", "/api/exports"),
    ("POST", "/api/exports/link-angle"),
    ("GET", "/api/hook-motion-presets"),
    ("GET", "/api/media/{file_path:path}"),
    ("POST", "/api/open-folder"),
    ("GET", "/api/post-log"),
    ("POST", "/api/post-log"),
    ("GET", "/api/post-log/pending"),
    ("GET", "/api/post-log/performance"),
    ("GET", "/api/post-log/summary"),
    ("PATCH", "/api/post-log/{post_id}/metrics"),
    ("POST", "/api/post-log/{post_id}/metrics"),
    ("GET", "/api/posts"),
    ("POST", "/api/posts"),
    ("GET", "/api/posts/performance"),
    ("GET", "/api/posts/summary"),
    ("PATCH", "/api/posts/{post_id}/metrics"),
    ("POST", "/api/posts/{post_id}/metrics"),
    ("POST", "/api/product/fetch"),
    ("GET", "/api/products"),
    ("POST", "/api/products"),
    ("POST", "/api/products/scrape-and-plan"),
    ("POST", "/api/products/scrape-and-plan-async"),
    ("POST", "/api/products/{product_id}/refresh-source"),
    ("POST", "/api/products/{product_id}/preview-source"),
    ("POST", "/api/products/{product_id}/preview-image-metadata"),
    ("DELETE", "/api/products/{product_id}"),
    ("PATCH", "/api/products/{product_id}"),
    ("PATCH", "/api/products/{product_id}/angles/{angle_id}"),
    ("PATCH", "/api/products/{product_id}/angles/{angle_id}/cover"),
    ("POST", "/api/products/{product_id}/angles/{angle_id}/reroll-script"),
    ("POST", "/api/products/{product_id}/angles/{angle_id}/videos"),
    ("POST", "/api/products/{product_id}/default-videos"),
    ("DELETE", "/api/products/{product_id}/videos"),
    ("POST", "/api/products/{product_id}/videos"),
    ("GET", "/api/projects"),
    ("DELETE", "/api/projects/{project_name}"),
    ("GET", "/api/projects/{project_name}"),
    ("PATCH", "/api/projects/{project_name}/clips"),
    ("PATCH", "/api/projects/{project_name}/cues"),
    ("GET", "/api/projects/{project_name}/origin"),
    ("PATCH", "/api/projects/{project_name}/state"),
    ("GET", "/api/raw-vault"),
    ("POST", "/api/raw-vault/batch-delete"),
    ("POST", "/api/raw-vault/reassign"),
    ("POST", "/api/render"),
    ("GET", "/api/render/status/{job_id}"),
    ("POST", "/api/reroll"),
    ("POST", "/api/script/ai-generate"),
    ("POST", "/api/script/generate"),
    ("GET", "/api/sfx"),
    ("GET", "/api/status"),
    ("POST", "/api/sub-srt/transcribe"),
    ("GET", "/api/tasks/active"),
    ("POST", "/api/tasks/clear-completed"),
    ("DELETE", "/api/tasks/{task_id}"),
    ("GET", "/api/tasks/{task_id}"),
    ("POST", "/api/tasks/{task_id}/cancel"),
    ("GET", "/api/tokens/history"),
    ("POST", "/api/tokens/reset"),
    ("GET", "/api/tokens/summary"),
    ("POST", "/api/upload"),
    ("GET", "/api/videos"),
    ("POST", "/api/videos/rename"),
    ("GET", "/api/voice/cache-status"),
    ("POST", "/api/voice/generate-cache"),
    ("GET", "/api/voice/presets"),
    ("POST", "/api/voice/preview"),
}


def test_all_expected_routes_are_registered():
    registered = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if not route.path.startswith("/docs") and not route.path.startswith("/redoc") and not route.path.startswith("/openapi")
    }
    missing = EXPECTED_API_ROUTES - registered
    assert not missing, f"Missing registered routes in FastAPI app: {missing}"


def test_public_reexports_exist_on_api_server():
    import scripts.api_server as server
    assert hasattr(server, "app"), "scripts.api_server must export 'app'"
    assert hasattr(server, "list_exports"), "scripts.api_server must export 'list_exports'"
    assert hasattr(server, "LinkAngleRequest"), "scripts.api_server must export 'LinkAngleRequest'"
    assert hasattr(server, "link_export_to_angle"), "scripts.api_server must export 'link_export_to_angle'"
    assert hasattr(server, "get_local_ip"), "scripts.api_server must export 'get_local_ip'"
