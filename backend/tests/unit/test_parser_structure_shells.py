import unittest

from backend.app.services.latex.parser import LatexParser


class TestParserStructureShells(unittest.TestCase):

    def setUp(self):
        self.parser = LatexParser(dir="dummy", output_dir="dummy")
        self.enc = self.parser._get_token_encoder()

    def test_annotate_section_chunk_extracts_leading_and_trailing_structure_shells(self):
        section = {
            "section": "1",
            "content": (
                "<PLACEHOLDER_ENV_3>\n\n"
                "\\end{snugshade*}\n\n"
                "\\newpage\n\n"
                "This paragraph should be translated.\n"
                "\\begin{appendix}"
            ),
        }

        annotated = self.parser._annotate_section_chunk(section, self.enc, 4000)

        self.assertTrue(annotated["contains_structure_shell"])
        self.assertFalse(annotated["structure_shell_only"])
        self.assertEqual(
            annotated["leading_structure_shell"],
            "<PLACEHOLDER_ENV_3>\n\n\\end{snugshade*}\n\n\\newpage\n\n",
        )
        self.assertEqual(
            annotated["core_translatable_content"],
            "This paragraph should be translated.",
        )
        self.assertEqual(annotated["trailing_structure_shell"], "\n\\begin{appendix}")
        self.assertFalse(annotated["immutable_only"])

    def test_structure_shell_only_chunk_becomes_immutable_passthrough(self):
        content = "<PLACEHOLDER_ENV_9>\n\\end{snugshade*}\n\\newpage"
        section = {"section": "1_chunk_2", "content": content}

        annotated = self.parser._annotate_section_chunk(section, self.enc, 4000)

        self.assertTrue(annotated["contains_structure_shell"])
        self.assertTrue(annotated["structure_shell_only"])
        self.assertTrue(annotated["immutable_only"])
        self.assertEqual(annotated["translation_status"], "immutable_passthrough")
        self.assertEqual(annotated["trans_content"], content)


if __name__ == "__main__":
    unittest.main()
