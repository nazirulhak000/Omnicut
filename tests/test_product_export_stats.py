# -*- coding: utf-8 -*-
"""Unit tests for product export_stats computation and 3-segment progress bar stats."""

import pytest
from scripts.product_store import ProductStore


def test_attach_export_stats_classifies_native_flow_and_hyperframes():
    fake_products = [
        {"id": "prod_1", "product_code": "HOY01", "name": "HOYAUP Fan", "angles": [{"angle_id": "ang_01"}]},
        {"id": "prod_2", "product_code": "HAT02", "name": "Hatari Max", "angles": [{"angle_id": "ang_01"}]},
        {"id": "prod_3", "product_code": "ESS04", "name": "Essager 100W", "angles": [{"angle_id": "ang_01"}]},
        {"id": "prod_4", "product_code": "VEO01", "name": "Veo Only Product", "angles": [{"angle_id": "ang_01"}]},
    ]
    fake_exports = [
        # Native exports for prod_1
        {"id": "e1", "product_id": "prod_1", "project_name": "HOY01-รีวิวสเปก_1", "path": "04_Exports/Ready_to_post/1.mp4"},
        {"id": "e2", "product_id": "prod_1", "project_name": "HOY01-ปัญหาก่อนใช้_1", "path": "04_Exports/Ready_to_post/2.mp4"},
        # HyperFrames exports for prod_1
        {"id": "e3", "product_id": "prod_1", "project_name": "_HyperFrames_Studio/hoy01-pov-s01", "path": "04_Exports/Ready_to_post/3.mp4"},
        # Duplicate record for same project (e.g. moved to posted) should deduplicate
        {"id": "e4", "product_id": "prod_1", "project_name": "HOY01-รีวิวสเปก_1", "path": "04_Exports/Posted/1.mp4"},

        # HyperFrames exports for prod_2
        {"id": "e5", "product_id": "prod_2", "project_name": "_HyperFrames_Studio/hat02-pov-s01", "path": "04_Exports/Ready_to_post/5.mp4"},
        {"id": "e6", "product_id": "prod_2", "project_name": "_HyperFrames_Studio/hat02-pov-s02", "path": "04_Exports/Ready_to_post/6.mp4"},

        # ESS04: 6 Native + 1 Flow (Veo AI)
        {"id": "e7", "product_id": "prod_3", "project_name": "ESS04-รีวิวสเปก_1", "path": "04_Exports/Ready_to_post/ess04_1.mp4"},
        {"id": "e8", "product_id": "prod_3", "project_name": "ESS04-เทียบของเดิม_1", "path": "04_Exports/Ready_to_post/ess04_2.mp4"},
        {"id": "e9", "product_id": "prod_3", "project_name": "ESS04-ทริกลึก_1", "path": "04_Exports/Ready_to_post/ess04_3.mp4"},
        {"id": "e10", "product_id": "prod_3", "project_name": "ESS04-เตือนภัย_1", "path": "04_Exports/Ready_to_post/ess04_4.mp4"},
        {"id": "e11", "product_id": "prod_3", "project_name": "ESS04-มุมมองผู้ใช้_1", "path": "04_Exports/Ready_to_post/ess04_5.mp4"},
        {"id": "e12", "product_id": "prod_3", "project_name": "ESS04-สรุปความคุ้ม_1", "path": "04_Exports/Ready_to_post/ess04_6.mp4"},
        # Flow (Veo AI) export for ESS04 (path has _AI_Veo_)
        {"id": "e13", "product_id": "prod_3", "project_name": "ESS04-ปัญหาก่อนใช้_1", "path": "04_Exports/Ready_to_post/20261114_233854_สายชาร์จเร็ว_Essager_100W_pain_point_AI_Veo_v1.mp4"},
        # Duplicate Veo export (re-rendered / updated) should deduplicate in Flow
        {"id": "e14", "product_id": "prod_3", "project_name": "ESS04-ปัญหาก่อนใช้_1", "path": "04_Exports/Ready_to_post/20261115_001759_สายชาร์จเร็ว_Essager_100W_pain_point_AI_Veo_v1.mp4"},

        # Flow only product (prod_4): test source_kind='flow' and format='flow' and ai_flow in path
        {"id": "e15", "product_id": "prod_4", "project_name": "VEO01-flow_job_01", "source_kind": "flow", "path": "04_Exports/Ready_to_post/veo_01.mp4"},
        {"id": "e16", "product_id": "prod_4", "project_name": "VEO01-flow_job_02", "format": "flow", "path": "04_Exports/Ready_to_post/veo_02.mp4"},
        {"id": "e17", "product_id": "prod_4", "project_name": "VEO01-flow_job_03", "path": "04_Exports/Ready_to_post/veo_ai_flow_03.mp4"},
    ]

    ProductStore._attach_export_stats(fake_products, fake_exports)

    p1 = fake_products[0]
    assert "export_stats" in p1
    assert p1["export_stats"]["native_count"] == 2
    assert p1["export_stats"]["flow_count"] == 0
    assert p1["export_stats"]["hyperframes_count"] == 1
    assert p1["export_stats"]["total_rendered"] == 3

    p2 = fake_products[1]
    assert "export_stats" in p2
    assert p2["export_stats"]["native_count"] == 0
    assert p2["export_stats"]["flow_count"] == 0
    assert p2["export_stats"]["hyperframes_count"] == 2
    assert p2["export_stats"]["total_rendered"] == 2

    # p3 (ESS04): 6 Native + 1 Flow = 7/7
    p3 = fake_products[2]
    assert "export_stats" in p3
    assert p3["export_stats"]["native_count"] == 6
    assert p3["export_stats"]["flow_count"] == 1
    assert p3["export_stats"]["hyperframes_count"] == 0
    assert p3["export_stats"]["total_rendered"] == 7

    # p4 (VEO01): 0 Native + 3 Flow + 0 HF = 3
    p4 = fake_products[3]
    assert "export_stats" in p4
    assert p4["export_stats"]["native_count"] == 0
    assert p4["export_stats"]["flow_count"] == 3
    assert p4["export_stats"]["hyperframes_count"] == 0
    assert p4["export_stats"]["total_rendered"] == 3


def test_to_lite_product_preserves_export_stats():
    prod = {
        "id": "p_test",
        "name": "Test Product",
        "product_code": "TST01",
        "angles": [
            {"angle_id": "ang_01", "status": "rendered", "source_kind": "hyperframes"},
            {"angle_id": "ang_02", "status": "rendered", "source_kind": "flow"},
            {"angle_id": "ang_03", "status": "rendered", "source_kind": "native"},
        ],
        "export_stats": {
            "native_count": 3,
            "flow_count": 2,
            "hyperframes_count": 5,
            "total_rendered": 10,
        },
    }
    lite = ProductStore._to_lite_product(prod, mode="compact")
    assert lite["export_stats"] == {
        "native_count": 3,
        "flow_count": 2,
        "hyperframes_count": 5,
        "total_rendered": 10,
    }
    assert lite["angles"][0]["source_kind"] == "hyperframes"
    assert lite["angles"][1]["source_kind"] == "flow"
    assert lite["angles"][2]["source_kind"] == "native"


def test_to_lite_product_default_export_stats_includes_flow_count():
    prod = {
        "id": "p_empty",
        "name": "Empty Product",
        "product_code": "EMP01",
        "angles": [],
    }
    lite = ProductStore._to_lite_product(prod, mode="compact")
    assert lite["export_stats"] == {
        "native_count": 0,
        "flow_count": 0,
        "hyperframes_count": 0,
        "total_rendered": 0,
    }


def test_reconcile_into_assigns_source_kind(tmp_path):
    projects_dir = tmp_path / "03_Projects"
    projects_dir.mkdir()
    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"
    exports_dir.mkdir(parents=True)
    posted_dir = tmp_path / "04_Exports" / "Posted"
    posted_dir.mkdir(parents=True)

    products = [
        {
            "id": "prod_1",
            "product_code": "TST01",
            "angles": [
                {"angle_id": "ang_01", "status": "scripted"},
                {"angle_id": "ang_02", "status": "scripted"},
                {"angle_id": "ang_03", "status": "scripted"},
            ],
        }
    ]

    export_records = [
        {
            "id": "exp_1",
            "product_id": "prod_1",
            "angle_id": "ang_01",
            "project_name": "TST01_pain_point_AI_Veo_v1",
            "path": "04_Exports/Ready_to_post/TST01_pain_point_AI_Veo_v1.mp4",
            "status": "rendered",
        },
        {
            "id": "exp_2",
            "product_id": "prod_1",
            "angle_id": "ang_02",
            "project_name": "_HyperFrames_Studio/tst01-pov-s01",
            "path": "04_Exports/Ready_to_post/tst01-pov-s01.mp4",
            "status": "rendered",
        },
        {
            "id": "exp_3",
            "product_id": "prod_1",
            "angle_id": "ang_03",
            "project_name": "TST01_spec_review_1",
            "path": "04_Exports/Ready_to_post/TST01_spec_review_1.mp4",
            "status": "rendered",
        },
    ]

    ProductStore._reconcile_into(products, projects_dir, exports_dir, posted_dir, export_records)

    angles = products[0]["angles"]
    assert angles[0]["source_kind"] == "flow"
    assert angles[0]["status"] == "rendered"
    assert angles[1]["source_kind"] == "hyperframes"
    assert angles[1]["status"] == "rendered"
    assert angles[2]["source_kind"] == "native"
    assert angles[2]["status"] == "rendered"
    # Ensure no DB row mutation occurs in _reconcile_into for export_stats
    assert "export_stats" not in products[0]

