import pytest
from backend.app.services.latex.utils import restore_mangled_placeholders

def test_restore_mangled_placeholders():
    expected_phs = [
        "<PLACEHOLDER_ENV_10>",
        "<PLACEHOLDER_CAP_1>",
        "<PLACEHOLDER_NEWCOMMAND_3>",
        "<PLACEHOLDER_input_path_begin>"
    ]
    
    # Text with various forms of mangled/escaped placeholders common to LLM translations
    mangled_tex = r"""
    Here is an equation <$PLACEHOLDER_ENV_10$> that was translated.
    Also consider Figure \textless PLACEHOLDER\_CAP\_1\textgreater which shows data.
    The new command \$<\$PLACEHOLDER\_NEWCOMMAND\_3\$>\$ is working.
    And a totally mangled input \langle PLACEHOLDER\_input\_path\_begin \rangle should be restored.
    """
    
    restored = restore_mangled_placeholders(mangled_tex, expected_phs)
    
    # Assert all expected exact placeholders are restored
    assert "<PLACEHOLDER_ENV_10>" in restored
    assert "<PLACEHOLDER_CAP_1>" in restored
    assert "<PLACEHOLDER_NEWCOMMAND_3>" in restored
    assert "<PLACEHOLDER_input_path_begin>" in restored
    
    # Assert the old mangled strings are no longer there (except if they were completely embedded in larger escapes, but the regex should consume them)
    assert "<$PLACEHOLDER_ENV_10$>" not in restored
    assert r"\textless" not in restored
    assert r"\langle" not in restored

def test_restore_mangled_placeholders_exact_matches():
    # If the text already contains exact matches, they should remain untouched without double-processing issues
    expected_phs = ["<PLACEHOLDER_ENV_10>"]
    tex = "Already correct: <PLACEHOLDER_ENV_10>"
    
    restored = restore_mangled_placeholders(tex, expected_phs)
    assert restored == "Already correct: <PLACEHOLDER_ENV_10>"
