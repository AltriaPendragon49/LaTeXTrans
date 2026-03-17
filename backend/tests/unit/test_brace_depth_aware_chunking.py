"""
Task 2: Structure-Aware Chunking — TDD Tests (Brace-Depth Guard)
=================================================================
Tests verifying that `_chunk_long_sections` never splits text
at a point where the LaTeX brace depth is > 0.

These tests define the RED phase. The implementation is extended
in `parser.py` to pass them (GREEN phase).
"""

import unittest
from backend.app.services.latex.parser import LatexParser


class TestBraceDepthAwareChunking(unittest.TestCase):

    def setUp(self):
        self.parser = LatexParser(dir="dummy", output_dir="dummy")

    def _set_section(self, content: str, section_id: str = "1"):
        self.parser.sections_json = [{
            "section": section_id,
            "content": content,
            "trans_content": "",
        }]

    def _get_chunks(self, max_tokens: int = 50):
        self.parser._chunk_long_sections(max_tokens=max_tokens)
        return self.parser.sections_json

    def test_does_not_split_inside_textbf_braces(self):
        """
        A long string fully inside \\textbf{...} must NOT be split
        at an inner sentence boundary if the split position is inside {}.
        """
        # Construct content where the long text is inside a macro argument
        inner = "This is a long sentence. " * 30  # ~150 tokens
        content = rf"\textbf{{{inner}}}"

        self._set_section(content)
        chunks = self._get_chunks(max_tokens=60)

        # Every chunk must have balanced braces
        for chunk in chunks:
            c = chunk["content"]
            depth = 0
            for ch in c:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
            self.assertEqual(
                depth, 0,
                msg=f"Chunk has unbalanced braces (depth={depth}): {c[:80]!r}"
            )

    def test_split_between_commands_at_depth_zero(self):
        """
        Two adjacent commands at brace depth 0, separated by a sentence boundary,
        should be safely split between them.
        """
        # Two big blocks at brace depth 0
        block_a = "Word " * 60 + "End sentence. "
        block_b = "More text " * 60 + "another sentence."
        content = block_a + "\n\n" + block_b

        self._set_section(content)
        chunks = self._get_chunks(max_tokens=80)

        self.assertGreater(len(chunks), 1, "Content should be split into multiple chunks")
        for chunk in chunks:
            c = chunk["content"]
            depth = 0
            for ch in c:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
            self.assertEqual(
                depth, 0,
                msg=f"Chunk after split has unbalanced braces: {c[:80]!r}"
            )

    def test_oversize_inside_brace_gets_flagged_not_split(self):
        """
        If a section is inside braces and can't be split without breaking depth,
        it must NOT be split and must be flagged as oversize_no_safe_boundary.
        """
        # A very long section enclosed in braces with no safe boundary
        inner = "AAAAAAAAAAAA " * 400  # Well over any token limit
        content = "{" + inner + "}"

        self._set_section(content)
        chunks = self._get_chunks(max_tokens=50)

        # Should be a single chunk (unsplittable), flagged as oversize
        self.assertEqual(len(chunks), 1, "Should not split when inside braces")
        self.assertTrue(
            chunks[0].get("oversize_no_safe_boundary", False),
            "Must set oversize_no_safe_boundary flag when unable to safely split"
        )

    def test_split_does_not_orphan_begin_end_pair(self):
        """
        A split must not separate \\begin{itemize} from its \\end{itemize}.
        The entire environment must stay in one chunk, or if too large,
        be flagged as oversize_no_safe_boundary.
        """
        # Build content where the env spans a large amount of text
        env_body = "\\item Long item text. " * 60
        env_content = f"\\begin{{itemize}}{env_body}\\end{{itemize}}"
        content = env_content

        self._set_section(content)
        chunks = self._get_chunks(max_tokens=100)

        for chunk in chunks:
            c = chunk["content"]
            begin_count = c.count("\\begin{itemize}")
            end_count = c.count("\\end{itemize}")
            self.assertEqual(
                begin_count, end_count,
                msg=(
                    f"\\begin{{itemize}} and \\end{{itemize}} counts mismatch in chunk: "
                    f"begins={begin_count}, ends={end_count}. Content: {c[:100]!r}"
                )
            )


if __name__ == "__main__":
    unittest.main()
