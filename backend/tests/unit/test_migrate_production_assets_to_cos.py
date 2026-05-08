import json
from pathlib import Path

from backend.scripts.migrate_production_assets_to_cos import (
    PathAlias,
    PathResolver,
    build_migration_plan,
    build_output_manifest,
    create_translated_source_archive,
    full_cos_key,
    MigrationContext,
)


def test_path_resolver_normalizes_host_alias_to_logical_data_path(tmp_path: Path) -> None:
    backend_root = tmp_path / "app" / "backend"
    host_root = "/srv/LaTexTrans/backend"
    source = backend_root / "data" / "uploads" / "task-1" / "main.tex"
    source.parent.mkdir(parents=True)
    source.write_text("hi", encoding="utf-8")

    resolver = PathResolver(
        base_dir=backend_root,
        aliases=[PathAlias(source=host_root, target=str(backend_root))],
    )

    assert resolver.resolve(f"{host_root}/data/uploads/task-1/main.tex") == source
    assert resolver.logical_data_path(f"{host_root}/data/uploads/task-1/main.tex") == "data/uploads/task-1/main.tex"


def test_full_cos_key_does_not_double_prefix() -> None:
    assert full_cos_key("data/uploads/task-1/main.tex", "latextrans-prod") == (
        "latextrans-prod/data/uploads/task-1/main.tex"
    )
    assert full_cos_key("latextrans-prod/data/uploads/task-1/main.tex", "latextrans-prod") == (
        "latextrans-prod/data/uploads/task-1/main.tex"
    )


def test_output_manifest_and_source_archive_are_generated_from_historical_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "data" / "outputs" / "task-1"
    paper_dir = output_dir / "paper"
    paper_dir.mkdir(parents=True)
    pdf_path = paper_dir / "paper_translated.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    (paper_dir / "main.tex").write_text("\\begin{document}Hi\\end{document}", encoding="utf-8")
    (paper_dir / "paper.log").write_text("ok", encoding="utf-8")
    (output_dir / "terminology_table.csv").write_text("a,b\n", encoding="utf-8")
    (output_dir / "task_log.json").write_text(
        json.dumps([{"event": "compilation_completed", "pdf_path": str(pdf_path)}]),
        encoding="utf-8",
    )

    manifest = build_output_manifest(output_dir)

    assert manifest == {
        "translated_pdf": "paper/paper_translated.pdf",
        "translated_source_archive": "_downloads/translated_source.zip",
        "terminology_csv": "terminology_table.csv",
        "logs": ["paper/paper.log"],
    }

    archive_path = tmp_path / "translated_source.zip"
    assert create_translated_source_archive(output_dir, archive_path)
    assert archive_path.exists()


def test_build_migration_plan_targets_assets_and_excludes_target_cos_from_orphans(tmp_path: Path) -> None:
    backend_root = tmp_path / "backend"
    community_pdf = backend_root / "data" / "community_papers" / "paper-1" / "translated" / "task-1-paper.pdf"
    upload_main = backend_root / "data" / "uploads" / "task-1" / "main.tex"
    output_dir = backend_root / "data" / "outputs" / "task-1"
    failed_dir = backend_root / "data" / "failed_tasks" / "task-fail"
    for path in [community_pdf, upload_main, output_dir / "paper" / "paper_translated.pdf", failed_dir / "error.json"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
    (output_dir / "paper" / "main.tex").write_text("source", encoding="utf-8")

    context = MigrationContext(
        base_dir=backend_root,
        cos_base_prefix="latextrans-prod",
        resolver=PathResolver(base_dir=backend_root),
    )
    target_key = "latextrans-prod/data/uploads/task-1/main.tex"
    plan = build_migration_plan(
        context=context,
        paper_assets=[
            {
                "id": "asset-1",
                "paper_id": "paper-1",
                "asset_type": "translated_pdf",
                "storage_backend": "local_disk",
                "file_path": str(community_pdf),
            }
        ],
        translation_tasks=[
            {
                "task_id": "task-1",
                "status": "completed",
                "source_path": str(upload_main.parent),
                "output_path": str(output_dir),
            }
        ],
        curation_jobs=[
            {
                "job_id": "job-1",
                "task_id": "task-fail",
                "status": "failed",
                "failed_artifact_path": str(failed_dir),
            }
        ],
        cos_objects={
            target_key: upload_main.stat().st_size,
            "latextrans-prod/data/outputs/orphan/task.log": 3,
        },
    )

    target_keys = plan.target_full_keys()
    assert target_key in target_keys
    assert "latextrans-prod/data/community_papers/paper-1/translated/task-1-paper.pdf" in target_keys
    assert "latextrans-prod/data/outputs/task-1/storage_manifest.json" in target_keys
    assert "latextrans-prod/data/outputs/task-1/_downloads/translated_source.zip" in target_keys
    assert "latextrans-prod/failed_tasks/task-fail/error.json" in target_keys
    assert plan.orphan_cos_keys == ["latextrans-prod/data/outputs/orphan/task.log"]
    assert not plan.conflicts
    assert not plan.missing_local_assets

    paper_update = next(item for item in plan.db_updates if item.table == "paper_assets")
    assert paper_update.fields == {
        "storage_backend": "object_storage",
        "file_path": "latextrans-prod/data/community_papers/paper-1/translated/task-1-paper.pdf",
    }
    task_update = next(item for item in plan.db_updates if item.table == "translation_tasks")
    assert task_update.fields == {
        "source_path": "data/uploads/task-1",
        "output_path": "data/outputs/task-1",
    }
    curation_update = next(item for item in plan.db_updates if item.table == "community_curation_jobs")
    assert curation_update.fields == {
        "artifact_storage_backend": "object_storage",
        "failed_artifact_path": "failed_tasks/task-fail",
    }


def test_build_migration_plan_reports_conflicting_cos_size(tmp_path: Path) -> None:
    backend_root = tmp_path / "backend"
    source = backend_root / "data" / "uploads" / "task-1" / "main.tex"
    source.parent.mkdir(parents=True)
    source.write_text("actual", encoding="utf-8")
    context = MigrationContext(
        base_dir=backend_root,
        cos_base_prefix="latextrans-prod",
        resolver=PathResolver(base_dir=backend_root),
    )

    plan = build_migration_plan(
        context=context,
        paper_assets=[],
        translation_tasks=[
            {
                "task_id": "task-1",
                "status": "failed",
                "source_path": str(source.parent),
                "output_path": "",
            }
        ],
        curation_jobs=[],
        cos_objects={"latextrans-prod/data/uploads/task-1/main.tex": 999},
    )

    assert plan.conflicts == [
        {
            "key": "latextrans-prod/data/uploads/task-1/main.tex",
            "existing_size": 999,
            "expected_size": source.stat().st_size,
        }
    ]
