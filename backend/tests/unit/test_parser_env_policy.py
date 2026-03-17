from backend.app.services.latex.parser import LatexParser


def test_level_a_theorem_like_envs_forced_non_translate():
    parser = LatexParser(dir="dummy", output_dir="dummy")
    text = r"\begin{theorem}A\end{theorem}\begin{proof}B\end{proof}\begin{definition}C\end{definition}"
    processed = parser._extract_envs(text)

    assert processed.count("<PLACEHOLDER_ENV_") == 3
    env_map = {item["env_name"]: item for item in parser.envs_json}
    assert env_map["theorem"]["need_trans"] is False
    assert env_map["proof"]["need_trans"] is False
    assert env_map["definition"]["need_trans"] is False


def test_custom_environment_remains_translatable_by_default():
    parser = LatexParser(dir="dummy", output_dir="dummy")
    text = r"\begin{customenv}Translate this text.\end{customenv}"
    processed = parser._extract_envs(text)

    assert "<PLACEHOLDER_ENV_1>" in processed
    assert len(parser.envs_json) == 1
    assert parser.envs_json[0]["env_name"] == "customenv"
    assert parser.envs_json[0]["need_trans"] is True
