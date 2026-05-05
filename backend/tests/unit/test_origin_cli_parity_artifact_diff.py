import asyncio
import importlib
import json
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

from backend.app.models.config_models import ORIGIN_CLI_PARITY_MODE


REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY_SRC_ROOT = REPO_ROOT / "texts" / "origin"
MAP_NAMES = (
    "inputs_map.json",
    "envs_map.json",
    "captions_map.json",
    "newcommands_map.json",
    "sections_map.json",
)


@contextmanager
def legacy_origin_imports():
    original_path = list(sys.path)
    removed_modules = {
        name: module
        for name, module in list(sys.modules.items())
        if name == "src" or name.startswith("src.")
    }
    for name in removed_modules:
        sys.modules.pop(name, None)
    sys.path.insert(0, str(LEGACY_SRC_ROOT))
    try:
        yield
    finally:
        for name in list(sys.modules):
            if name == "src" or name.startswith("src."):
                sys.modules.pop(name, None)
        sys.modules.update(removed_modules)
        sys.path[:] = original_path


def _write_fixture(project_dir: Path) -> None:
    project_dir.mkdir(parents=True)
    (project_dir / "main.tex").write_text(
        "\n".join(
            [
                r"\documentclass{article}",
                r"\newcommand{\method}{ParityCheck}",
                r"\title{Origin CLI Parity}",
                r"\begin{document}",
                r"\maketitle",
                r"\input{intro}",
                r"\section{Method}",
                r"The backend path should mirror the origin CLI parser.",
                r"\begin{figure}",
                r"\centering",
                r"\caption{A deterministic caption}",
                r"\end{figure}",
                r"\end{document}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (project_dir / "intro.tex").write_text(
        "\n".join(
            [
                r"\section{Intro}",
                r"This short fixture avoids network calls and real LLM output.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _copy_project(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst)


def _parity_config() -> dict:
    return {
        "source_language": "en",
        "target_language": "zh",
        "translation_core_mode": ORIGIN_CLI_PARITY_MODE,
        "enable_legacy_translation_core": True,
        "enable_parser_env_llm_judgment": True,
        "llm_config": {
            "model": "gpt-4o",
            "base_url": "http://test-llm.local",
            "api_key": "test-api-key",
        },
    }


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def _inject_deterministic_translations(map_dir: Path) -> None:
    sections = _read_json(map_dir / "sections_map.json")
    for section in sections:
        if section.get("section") in {"-1", "0"}:
            section["trans_content"] = section["content"]
        else:
            section["trans_content"] = section["content"].replace(
                "This short fixture avoids network calls and real LLM output.",
                "确定性译文避免网络调用和真实 LLM 输出。",
            ).replace(
                "The backend path should mirror the origin CLI parser.",
                "后端路径应镜像 origin CLI 解析器。",
            )
    _write_json(map_dir / "sections_map.json", sections)

    captions = _read_json(map_dir / "captions_map.json")
    for caption in captions:
        caption["trans_content"] = caption["content"].replace(
            "Origin CLI Parity",
            "Origin CLI 奇偶校验",
        ).replace(
            "A deterministic caption",
            "确定性图题",
        )
    _write_json(map_dir / "captions_map.json", captions)

    envs = _read_json(map_dir / "envs_map.json")
    for env in envs:
        env["trans_content"] = env["content"]
    _write_json(map_dir / "envs_map.json", envs)


def _construct_backend(project_dir: Path, map_dir: Path, output_dir: Path) -> Path:
    from backend.app.services.latex.reconstruct import LatexConstructor

    shutil.copytree(project_dir, output_dir)
    constructor = LatexConstructor(
        sections=_read_json(map_dir / "sections_map.json"),
        captions=_read_json(map_dir / "captions_map.json"),
        envs=_read_json(map_dir / "envs_map.json"),
        inputs=_read_json(map_dir / "inputs_map.json"),
        newcommands=_read_json(map_dir / "newcommands_map.json"),
        output_latex_dir=str(output_dir),
        target_language="zh",
        origin_cli_parity=True,
    )
    constructor.construct()
    return output_dir / "main.tex"


def _construct_legacy(project_dir: Path, map_dir: Path, output_dir: Path) -> Path:
    shutil.copytree(project_dir, output_dir)
    with legacy_origin_imports():
        reconstruct_mod = importlib.import_module("src.formats.latex.reconstruct")
        constructor = reconstruct_mod.LatexConstructor(
            sections=_read_json(map_dir / "sections_map.json"),
            captions=_read_json(map_dir / "captions_map.json"),
            envs=_read_json(map_dir / "envs_map.json"),
            inputs=_read_json(map_dir / "inputs_map.json"),
            newcommands=_read_json(map_dir / "newcommands_map.json"),
            output_latex_dir=str(output_dir),
        )
        constructor.construct()
    return output_dir / "main.tex"


def _run_legacy_parser(project_dir: Path, output_dir: Path) -> None:
    with legacy_origin_imports():
        parser_agent_mod = importlib.import_module("src.agents.tool_agents.parser_agent")
        agent = parser_agent_mod.ParserAgent(
            config=_parity_config(),
            project_dir=str(project_dir),
            output_dir=str(output_dir),
        )
        agent.execute()


def _run_backend_parity_parser(project_dir: Path, output_dir: Path) -> None:
    from backend.app.services.agents.parser_agent import ParserAgent

    agent = ParserAgent(
        config=_parity_config(),
        project_dir=str(project_dir),
        output_dir=str(output_dir),
    )
    asyncio.run(agent.execute())


class _CapturingLLMSession:
    def __init__(self):
        self.calls = []

    def post(self, url, json, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "payload": json,
                "headers": headers,
                "timeout": getattr(timeout, "total", timeout),
            }
        )
        return _FakeLLMResponse()


class _FakeLLMResponse:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def json(self):
        return {"choices": [{"message": {"content": "deterministic translation"}}]}


def test_backend_origin_cli_parity_matches_legacy_maps_and_reconstructed_tex(tmp_path):
    source_project = tmp_path / "source"
    _write_fixture(source_project)

    legacy_project = tmp_path / "legacy_project"
    backend_project = tmp_path / "backend_project"
    _copy_project(source_project, legacy_project)
    _copy_project(source_project, backend_project)

    legacy_maps = tmp_path / "legacy_maps"
    backend_maps = tmp_path / "backend_maps"
    legacy_maps.mkdir()
    backend_maps.mkdir()

    _run_legacy_parser(legacy_project, legacy_maps)
    _run_backend_parity_parser(backend_project, backend_maps)

    for name in MAP_NAMES:
        assert (backend_maps / name).read_bytes() == (legacy_maps / name).read_bytes(), name

    _inject_deterministic_translations(legacy_maps)
    _inject_deterministic_translations(backend_maps)

    for name in MAP_NAMES:
        assert (backend_maps / name).read_bytes() == (legacy_maps / name).read_bytes(), name

    legacy_main = _construct_legacy(legacy_project, legacy_maps, tmp_path / "legacy_reconstructed")
    backend_main = _construct_backend(backend_project, backend_maps, tmp_path / "backend_reconstructed")

    assert backend_main.read_bytes() == legacy_main.read_bytes()


def test_backend_origin_cli_parity_translator_payloads_match_legacy_cli():
    from backend.app.models.config_models import normalize_origin_cli_parity_agent_config
    from backend.app.services.agents.translator_agent import TranslatorAgent
    from backend.app.services.latex import prompts as backend_prompts

    config = normalize_origin_cli_parity_agent_config(_parity_config())

    with legacy_origin_imports():
        legacy_translator_mod = importlib.import_module("src.agents.tool_agents.translator_agent")
        legacy_prompts = importlib.import_module("src.formats.latex.prompts")
        legacy_prompts.init_prompts("en", "zh")
        legacy_agent = legacy_translator_mod.TranslatorAgent(
            config=config,
            project_dir="project",
            output_dir="output",
        )
        legacy_session = _CapturingLLMSession()
        asyncio.run(
            legacy_agent._request_llm_for_trans(
                legacy_prompts.section_system_prompt,
                "Section text.",
                fail_part="1",
                type="sec",
                session=legacy_session,
            )
        )
        asyncio.run(
            legacy_agent._request_llm_for_retrans_error_parts(
                legacy_prompts.retrans_error_parts_system_prompt,
                part={
                    "content": "Original text.",
                    "trans_content": "Translated text.",
                },
                error_message="placeholder mismatch",
                fail_part="1",
                type="sec",
                session=legacy_session,
            )
        )

    backend_agent = TranslatorAgent(
        config=config,
        project_dir="project",
        output_dir="output",
    )
    backend_agent.prompts = backend_prompts.create_origin_cli_parity_prompts("en", "zh")
    backend_session = _CapturingLLMSession()
    asyncio.run(
        backend_agent._legacy_request_llm_for_trans(
            backend_agent.prompts["section_system_prompt"],
            "Section text.",
            fail_part="1",
            type="sec",
            session=backend_session,
        )
    )
    asyncio.run(
        backend_agent._legacy_request_llm_for_retrans_error_parts(
            backend_agent.prompts["retrans_error_parts_system_prompt"],
            part={
                "content": "Original text.",
                "trans_content": "Translated text.",
            },
            error_message="placeholder mismatch",
            fail_part="1",
            type="sec",
            session=backend_session,
        )
    )

    assert backend_session.calls == legacy_session.calls


def test_backend_origin_cli_parity_prompts_are_backend_owned_and_match_legacy():
    import inspect

    from backend.app.services.latex import origin_cli_prompts as owned_origin_prompts
    from backend.app.services.latex import prompts as backend_prompts

    backend_snapshot = backend_prompts.create_origin_cli_parity_prompts("en", "zh")
    with legacy_origin_imports():
        legacy_prompts = importlib.import_module("src.formats.latex.prompts")
        legacy_prompts.init_prompts("en", "zh")
        legacy_snapshot = {
            key: getattr(legacy_prompts, key)
            for key in backend_prompts._PROMPT_KEYS
        }

    assert backend_snapshot == legacy_snapshot
    assert "backend/app/services/latex/origin_cli_prompts.py" in Path(
        owned_origin_prompts.__file__
    ).as_posix()
    assert "texts/origin" not in inspect.getsource(
        backend_prompts.create_origin_cli_parity_prompts
    )


def test_backend_origin_cli_parity_production_code_has_no_legacy_origin_runtime_dependency():
    production_roots = [
        REPO_ROOT / "backend" / "app",
        REPO_ROOT / "backend" / "scripts",
        REPO_ROOT / "backend" / "migrations",
        REPO_ROOT / "backend" / "migrations_mysql",
    ]
    production_files = [REPO_ROOT / "backend" / "__init__.py"]
    forbidden_markers = (
        "texts/origin",
        "texts\\origin",
        "origin/src",
        "origin\\src",
        "src.formats",
        "src.agents",
        "importlib.util",
        "spec_from_file_location",
        "_load_origin_cli",
        "LEGACY_SRC_ROOT",
        "legacy_origin_imports",
    )
    offenders = []

    paths = []
    for root in production_roots:
        if root.exists():
            paths.extend(root.rglob("*.py"))
    paths.extend(path for path in production_files if path.exists())

    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in forbidden_markers:
            if marker in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)} contains {marker!r}")

    assert offenders == []


def test_backend_origin_cli_parity_parser_env_judgment_uses_origin_prompt_snapshot(
    monkeypatch,
    tmp_path,
):
    import backend.app.services.agents.parser_agent as backend_parser_agent

    project_dir = tmp_path / "prompt_project"
    output_dir = tmp_path / "prompt_maps"
    _write_fixture(project_dir)
    seen_payloads = []

    class FakeLatexParser:
        def __init__(self, *_args, **_kwargs):
            self.inputs_json = []
            self.envs_json = [
                {
                    "placeholder": "<PLACEHOLDER_ENV_1>",
                    "env_name": "theorem",
                    "content": r"\begin{theorem}Needs judgment.\end{theorem}",
                    "trans_content": "",
                    "need_trans": True,
                }
            ]
            self.captions_json = []
            self.newcommands_json = []
            self.sections_json = []

        def parse(self, *_args, **_kwargs):
            return None

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "true"}}]}

    def fake_post(_url, json, headers, timeout):
        del headers, timeout
        seen_payloads.append(json)
        return FakeResponse()

    monkeypatch.setattr(
        backend_parser_agent.pm,
        "create_prompts",
        lambda *_args, **_kwargs: {"set_need_trans_for_envs_system_prompt": "backend prompt"},
    )
    monkeypatch.setattr(
        backend_parser_agent.pm,
        "create_origin_cli_parity_prompts",
        lambda *_args, **_kwargs: {"set_need_trans_for_envs_system_prompt": "origin prompt"},
    )
    monkeypatch.setattr(backend_parser_agent, "LatexParser", FakeLatexParser)
    monkeypatch.setattr(backend_parser_agent.requests, "post", fake_post)

    agent = backend_parser_agent.ParserAgent(
        config=_parity_config(),
        project_dir=str(project_dir),
        output_dir=str(output_dir),
    )

    asyncio.run(agent.execute())

    assert seen_payloads[0]["messages"][0]["content"] == "origin prompt"


@pytest.mark.parametrize(
    ("pdf_engine", "expected_status", "expected_sequence"),
    [
        ("pdflatex", "completed", ["pdflatex"]),
        ("xelatex", "completed", ["pdflatex", "xelatex"]),
        (None, "failed_compilation", ["pdflatex", "xelatex"]),
    ],
)
def test_backend_origin_cli_parity_matches_legacy_compile_sequence(
    monkeypatch,
    tmp_path,
    pdf_engine,
    expected_status,
    expected_sequence,
):
    tex_dir = tmp_path / "compile_project"
    _write_fixture(tex_dir)
    tex_file = tex_dir / "main.tex"

    run_calls = []
    with legacy_origin_imports():
        legacy_compile_mod = importlib.import_module("src.formats.latex.compile")

        def fake_run(cmd, check, capture_output, cwd):
            engine = next(part[1:] for part in cmd if part in {"-pdflatex", "-xelatex", "-lualatex"})
            out_dir = Path(next(part.split("=", 1)[1] for part in cmd if part.startswith("-outdir=")))
            run_calls.append((engine, out_dir.name, Path(cmd[-1]).name, check, capture_output, Path(cwd)))
            out_dir.mkdir(parents=True, exist_ok=True)
            if engine == pdf_engine:
                (out_dir / "main.pdf").write_bytes(b"%PDF")
                return subprocess.CompletedProcess(cmd, 0, b"", b"")
            (out_dir / "main.log").write_text("failed", encoding="utf-8")
            raise subprocess.CalledProcessError(1, cmd)

        monkeypatch.setattr(legacy_compile_mod.subprocess, "run", fake_run)
        legacy_pdf = legacy_compile_mod.LaTexCompiler(str(tex_dir)).compile()
        legacy_calls = list(run_calls)

    from backend.app.services.latex import compiler as backend_compiler

    run_calls.clear()
    backend_result = backend_compiler.compile_with_origin_cli_parity(str(tex_file), str(tex_dir))
    backend_calls = list(run_calls)

    legacy_status = "completed" if legacy_pdf else "failed_compilation"

    assert [call[0] for call in backend_calls] == [call[0] for call in legacy_calls] == expected_sequence
    assert backend_calls == legacy_calls
    assert backend_result["status"] == legacy_status == expected_status


def test_backend_origin_cli_parity_compiler_uses_legacy_latexmk_command(
    monkeypatch,
    tmp_path,
):
    from backend.app.services.latex import compiler as backend_compiler

    tex_dir = tmp_path / "compile_command_project"
    _write_fixture(tex_dir)
    tex_file = tex_dir / "main.tex"
    calls = []

    def forbidden_compile_latex(*_args, **_kwargs):
        raise AssertionError("origin parity compiler must not call modern compile_latex")

    def fake_run(cmd, check, capture_output, cwd):
        calls.append(
            {
                "cmd": list(cmd),
                "check": check,
                "capture_output": capture_output,
                "cwd": Path(cwd),
            }
        )
        out_dir = Path(next(part.split("=", 1)[1] for part in cmd if part.startswith("-outdir=")))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "main.pdf").write_bytes(b"%PDF")
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(backend_compiler, "compile_latex", forbidden_compile_latex)
    monkeypatch.setattr(backend_compiler.subprocess, "run", fake_run)

    result = backend_compiler.compile_with_origin_cli_parity(str(tex_file), str(tex_dir))

    assert result["status"] == "completed"
    assert result["engine"] == "pdflatex"
    assert calls == [
        {
            "cmd": [
                "latexmk",
                "-pdflatex",
                "-interaction=nonstopmode",
                f"-outdir={tex_dir / 'build_pdflatex'}",
                "-file-line-error",
                "-synctex=1",
                "-f",
                str(tex_file),
            ],
            "check": True,
            "capture_output": True,
            "cwd": tex_dir,
        }
    ]
