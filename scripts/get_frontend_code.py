from pathlib import Path
from typing import Iterable


INCLUDED_DIRECTORIES = (
    "pages",
    "features",
    "contexts",
    "layout",
    "theme",
    "lib",
    "types",
    "ui",
    "i18n",
)

INCLUDED_ENTRY_FILES = (
    "main.tsx",
    "App.tsx",
    "layout.tsx",
    "api-base.ts",
    "i18n.ts",
)

STYLE_EXTENSIONS = (".css", ".scss", ".sass", ".less")
SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
ALLOWED_EXTENSIONS = SOURCE_EXTENSIONS + STYLE_EXTENSIONS


def build_file_tree(source_root: Path, files: Iterable[Path]) -> str:
    tree: dict[str, dict] = {}

    for file_path in files:
        current_level = tree
        for part in file_path.relative_to(source_root).parts:
            current_level = current_level.setdefault(part, {})

    lines = [source_root.as_posix()]

    def walk(node: dict[str, dict], prefix: str = "") -> None:
        keys = sorted(node.keys())
        for index, key in enumerate(keys):
            is_last = index == len(keys) - 1
            connector = "`-- " if is_last else "|-- "
            lines.append(f"{prefix}{connector}{key}")
            child_prefix = f"{prefix}{'    ' if is_last else '|   '}"
            walk(node[key], child_prefix)

    walk(tree)
    return "\n".join(lines)


def is_in_included_directory(source_root: Path, path: Path) -> bool:
    relative_path = path.relative_to(source_root)
    return bool(relative_path.parts) and relative_path.parts[0] in INCLUDED_DIRECTORIES


def is_test_file(path: Path) -> bool:
    lower_name = path.name.lower()
    lower_parts = {part.lower() for part in path.parts}
    return ".test." in lower_name or ".spec." in lower_name or "__tests__" in lower_parts or "test" in lower_parts


def detect_language(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".module.css":
        return "css"
    return suffix[1:] if suffix else "text"


def should_include_file(source_root: Path, path: Path) -> bool:
    if not path.is_file():
        return False

    suffix = path.suffix.lower()
    relative_path = path.relative_to(source_root)

    if relative_path.as_posix() in INCLUDED_ENTRY_FILES:
        return True

    if is_test_file(path):
        return False

    if suffix in STYLE_EXTENSIONS:
        return True

    if suffix not in ALLOWED_EXTENSIONS:
        return False

    return is_in_included_directory(source_root, path)


def classify_excluded_file(source_root: Path, path: Path) -> str:
    relative_path = path.relative_to(source_root).as_posix()
    suffix = path.suffix.lower()

    if is_test_file(path):
        return "test"
    if relative_path.startswith("locales/"):
        return "locale"
    if suffix in {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".woff", ".woff2", ".ttf", ".otf", ".mp3", ".mp4", ".webm", ".pdf", ".zip"}:
        return "asset"
    return "other"


def render_bundle(source_root: Path, files: Iterable[Path]) -> str:
    resolved_root = source_root.resolve()
    file_list = list(files)
    lines: list[str] = [
        "# Frontend Source Bundle",
        "",
        f"Source root: {resolved_root}",
        "",
        "## File Tree",
        "",
        "```text",
        build_file_tree(resolved_root, file_list),
        "```",
        "",
    ]

    for file_path in file_list:
        resolved_file = file_path.resolve()
        relative_path = resolved_file.relative_to(resolved_root)
        language = detect_language(file_path)
        content = file_path.read_text(encoding="utf-8")

        lines.extend(
            [
                f"## File: {resolved_file}",
                f"Relative path: {relative_path}",
                "",
                f"```{language}",
                content,
                "```",
                "",
            ]
        )

    if not file_list:
        lines.extend(["No matching files found.", ""])

    return "\n".join(lines)


def render_excluded_resources(resources: list[tuple[str, Path]]) -> str:
    lines = ["## Excluded Resources", ""]

    if not resources:
        lines.extend(["None", ""])
        return "\n".join(lines)

    for label, path in resources:
        lines.append(f"- {label}: {path.resolve()}")

    lines.append("")
    return "\n".join(lines)


def pack_source_tree_to_markdown(
    source_root: Path | None = None,
    output_path: Path | None = None,
    extensions: Iterable[str] = ALLOWED_EXTENSIONS,
) -> Path:
    script_root = Path(__file__).resolve().parent.parent
    resolved_source_root = (source_root or script_root / "frontend" / "src").resolve()
    resolved_output_path = (output_path or script_root / "frontend_src_code_bundle.md").resolve()

    normalized_extensions = {extension.lower() for extension in extensions}
    all_files = sorted(
        [path for path in resolved_source_root.rglob("*") if path.is_file()],
        key=lambda path: str(path.resolve()).lower(),
    )
    included_files = [
        path
        for path in all_files
        if should_include_file(resolved_source_root, path)
        and (path.suffix.lower() in normalized_extensions or path.relative_to(resolved_source_root).as_posix() in INCLUDED_ENTRY_FILES)
    ]
    included_set = {path.resolve() for path in included_files}
    excluded_resources = [
        (classify_excluded_file(resolved_source_root, path), path)
        for path in all_files
        if path.resolve() not in included_set
    ]

    bundle_content = "\n".join(
        [
            render_bundle(resolved_source_root, included_files),
            render_excluded_resources(excluded_resources),
        ]
    )
    resolved_output_path.write_text(bundle_content, encoding="utf-8")

    return resolved_output_path


def main() -> None:
    output_path = pack_source_tree_to_markdown()
    print(f"Bundle written to: {output_path}")


if __name__ == "__main__":
    main()
