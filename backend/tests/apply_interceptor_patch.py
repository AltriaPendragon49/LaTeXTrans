"""
Apply/remove runtime config-capture patch in translate.py for compatibility.

Usage:
    python tests/apply_interceptor_patch.py       # apply patch (or no-op if integrated)
    python tests/apply_interceptor_patch.py undo  # undo patch
"""

import sys
from pathlib import Path


TARGET_FILE = Path(__file__).parent.parent / "app" / "api" / "routes" / "translate.py"
INSERTION_MARKER = "Agent config: mode="
PATCH_MARKER = "# ========== CONFIG CAPTURE RUNTIME PATCH - START =========="
BUILTIN_MARKERS = [
    "from backend.app.services.config_capture import capture_task_config",
    "captured_config_file = capture_task_config(",
]

INTERCEPTOR_CODE = '''
        # ========== CONFIG CAPTURE RUNTIME PATCH - START ==========
        try:
            from backend.app.services.config_capture import capture_task_config as _capture_task_config

            _captured_config_file = _capture_task_config(
                task_id=task_id,
                advanced_config=advanced_config.model_dump(),
                agent_config=agent_config,
                llm_config=llm_config,
                additional_info={
                    "arxiv_id": arxiv_id,
                    "is_logged_in": bool(user_id),
                    "user_id": user_id,
                    "task_id": task_id,
                    "target_language": target_language,
                    "source_language": source_language,
                    "source_path": str(source_path),
                    "output_dir": str(output_dir),
                },
            )
            if _captured_config_file:
                logger.info(f"Task config snapshot saved: {_captured_config_file}")
        except Exception as _capture_error:
            logger.warning(f"Runtime config capture patch failed: {_capture_error}")
        # ========== CONFIG CAPTURE RUNTIME PATCH - END ==========
'''


def _already_patched(lines: list[str]) -> bool:
    return any(PATCH_MARKER in line for line in lines)


def _builtin_integrated(content: str) -> bool:
    return all(marker in content for marker in BUILTIN_MARKERS)


def apply_patch() -> bool:
    """Apply patch for branches that don't yet include built-in runtime capture."""
    if not TARGET_FILE.exists():
        print(f"ERROR: target file not found: {TARGET_FILE}")
        return False

    with open(TARGET_FILE, "r", encoding="utf-8") as file:
        content = file.read()
    lines = content.splitlines(keepends=True)

    if _builtin_integrated(content):
        print("Runtime config capture is already integrated in translate.py. No patch needed.")
        return True

    if _already_patched(lines):
        print("Runtime patch already applied. Nothing to do.")
        return True

    insert_index = None
    for i, line in enumerate(lines):
        if INSERTION_MARKER in line:
            j = i + 1
            while j < len(lines) and (
                lines[j].strip().startswith('f"')
                or lines[j].strip().startswith('"')
                or "verify=" in lines[j]
            ):
                j += 1
            insert_index = j
            break

    if insert_index is None:
        print(f"ERROR: insertion marker not found: {INSERTION_MARKER}")
        return False

    backup_file = TARGET_FILE.with_suffix(".py.backup")
    with open(backup_file, "w", encoding="utf-8") as file:
        file.write(content)

    lines.insert(insert_index, INTERCEPTOR_CODE)
    with open(TARGET_FILE, "w", encoding="utf-8") as file:
        file.writelines(lines)

    print(f"Runtime config capture patch applied: {TARGET_FILE}")
    print(f"Backup file: {backup_file}")
    print(f"Inserted around line: {insert_index + 1}")
    return True


def undo_patch() -> bool:
    """Undo patch by restoring backup file."""
    backup_file = TARGET_FILE.with_suffix(".py.backup")

    if not backup_file.exists():
        print(f"ERROR: backup file not found: {backup_file}")
        return False

    with open(backup_file, "r", encoding="utf-8") as file:
        content = file.read()

    with open(TARGET_FILE, "w", encoding="utf-8") as file:
        file.write(content)

    print(f"Original file restored: {TARGET_FILE}")
    print(f"You may delete backup file manually: {backup_file}")
    return True


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "undo":
        print("Undoing runtime config capture patch...")
        undo_patch()
        return

    print("Applying runtime config capture patch...")
    success = apply_patch()
    if not success:
        return

    print("\n" + "=" * 60)
    print("Patch check completed")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start backend service")
    print("2. Run translation from frontend")
    print("3. Check backend/data/task_configs/")
    print("4. Run validator:")
    print("   python tests/config_validator.py data/task_configs/config_*.json")
    print("\nUndo patch: python tests/apply_interceptor_patch.py undo")


if __name__ == "__main__":
    main()
