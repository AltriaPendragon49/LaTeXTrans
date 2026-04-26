import unittest
from backend.app.services.latex import parser as parser_module
from backend.app.services.latex.parser import LatexParser
import tiktoken

class TestLatexParserChunking(unittest.TestCase):
    def setUp(self):
        # Instantiate with dummy directories
        self.parser = LatexParser(dir="dummy", output_dir="dummy")
        
    def test_chunk_long_sections_basic_paragraph_split(self):
        # We test that a 2 paragraph text gets split properly over the max token limit
        p1 = "This is a short paragraph. " * 50
        p2 = "This is another paragraph. " * 50
        
        long_content = p1 + "\n\n" + p2
        
        self.parser.sections_json = [
            {
                "section": "1",
                "content": long_content,
                "trans_content": ""
            }
        ]
        
        # Determine tokens so we can pick a max slightly above one paragraph
        enc = tiktoken.get_encoding("cl100k_base")  # gpt-4o uses cl100k_base
        tokens_p1 = len(enc.encode(p1))
        
        # Max tokens should be enough to hold p1, but not p1+p2
        self.parser._chunk_long_sections(max_tokens=tokens_p1 + 20)
        
        self.assertEqual(len(self.parser.sections_json), 2)
        self.assertEqual(self.parser.sections_json[0]["section"], "1_chunk_1")
        self.assertEqual(self.parser.sections_json[1]["section"], "1_chunk_2")
        
        # The first chunk should just be p1
        self.assertEqual(self.parser.sections_json[0]["content"].strip(), p1.strip())
        
        self.assertEqual(self.parser.sections_json[1]["content"].strip(), p2.strip())
        # The stored context should be a substring of the end of p1
        self.assertTrue(self.parser.sections_json[1]["previous_context"].strip() in p1)
        self.assertTrue(len(self.parser.sections_json[1]["previous_context"]) > 100)
    def test_chunk_long_sections_sentence_fallback(self):
        # Test what happens when a single paragraph is larger than the max_tokens limit
        s1 = "This is the first long sentence. "
        s2 = "This is the second long sentence. "
        s3 = "This is the third long sentence. "
        
        # Single giant paragraph with no \n\n
        content = (s1 * 50) + (s2 * 50) + (s3 * 50)

        self.parser.sections_json = [
            {
                "section": "1",
                "content": content,
                "trans_content": ""
            }
        ]
        
        enc = tiktoken.get_encoding("cl100k_base")  # gpt-4o uses cl100k_base
        tokens_s1 = len(enc.encode(s1 * 50))
        
        self.parser._chunk_long_sections(max_tokens=tokens_s1 + 20)
        
        # It should split successfully despite having no paragraph breaks
        self.assertTrue(len(self.parser.sections_json) > 1)
        
        # Verify previous_context is working fine even on sentence boundaries
        self.assertIn("previous_context", self.parser.sections_json[1])
        self.assertTrue(len(self.parser.sections_json[1]["previous_context"]) > 0)

    def test_chunking_maintains_placeholders(self):
        # Ensure that splitting doesn't orphan placeholders by separating begin/end etc...
        # Also just basic validation that placeholders exist correctly.
        p1 = "Paragraph 1 with a <PLACEHOLDER_CAP_1>. " * 20
        p2 = "\n\nParagraph 2 with <PLACEHOLDER_ENV_1>. " * 20
        
        self.parser.sections_json = [
            {
                "section": "1",
                "content": p1 + p2,
                "trans_content": ""
            }
        ]
        
        self.parser._chunk_long_sections(max_tokens=100)
        self.assertTrue(len(self.parser.sections_json) > 1)
        
        # Check that we haven't lost any placeholder tags
        combined_result = " ".join([ch["content"] for ch in self.parser.sections_json])
        self.assertIn("<PLACEHOLDER_CAP_1>", combined_result)
        self.assertIn("<PLACEHOLDER_ENV_1>", combined_result)
        
    def test_chunk_skip_short_sections(self):
        short_content = "This is a very short text, well under any limit."
        self.parser.sections_json = [
            {
                "section": "1",
                "content": short_content,
                "trans_content": ""
            }
        ]
        
        self.parser._chunk_long_sections(max_tokens=4000)
        self.assertEqual(len(self.parser.sections_json), 1)
        self.assertEqual(self.parser.sections_json[0]["section"], "1")
        self.assertNotIn("previous_context", self.parser.sections_json[0])

    def test_oversize_no_safe_boundary_flag_when_single_part_exceeds_limit(self):
        # No sentence boundary ". " and no paragraph boundary "\n\n", so chunk stays oversize.
        long_unsplittable = ("A" * 12000) + "\n"
        self.parser.sections_json = [
            {
                "section": "2",
                "content": long_unsplittable,
                "trans_content": ""
            }
        ]

        self.parser._chunk_long_sections(max_tokens=200)

        self.assertEqual(len(self.parser.sections_json), 1)
        chunk = self.parser.sections_json[0]
        self.assertEqual(chunk["section"], "2_chunk_1")
        self.assertTrue(chunk.get("oversize_no_safe_boundary", False))
        self.assertGreater(chunk.get("chunk_token_count", 0), 200)

    def test_placeholder_only_chunks_are_not_left_isolated(self):
        paragraph_a = ("Natural language before split. " * 80).strip()
        placeholder_only = "\n\n<PLACEHOLDER_ENV_25>\n\n"
        paragraph_b = ("Natural language after split. " * 80).strip()

        self.parser.sections_json = [
            {
                "section": "10",
                "content": paragraph_a + placeholder_only + paragraph_b,
                "trans_content": "",
            }
        ]

        self.parser._chunk_long_sections(max_tokens=120)

        isolated_placeholder_chunks = [
            chunk for chunk in self.parser.sections_json
            if chunk.get("content", "").strip() == "<PLACEHOLDER_ENV_25>"
        ]
        self.assertEqual(isolated_placeholder_chunks, [])
        self.assertTrue(all(chunk.get("chunk_kind") != "placeholder_only" for chunk in self.parser.sections_json))
        self.assertTrue(all("immutable_only" in chunk for chunk in self.parser.sections_json))

    def test_chunking_falls_back_when_tiktoken_encoding_download_fails(self):
        def _raise_encoding_error(_name):
            raise RuntimeError("offline tiktoken cache")

        original_get_encoding = parser_module.tiktoken.get_encoding
        parser_module.tiktoken.get_encoding = _raise_encoding_error
        try:
            self.parser.sections_json = [
                {
                    "section": "1",
                    "content": ("Offline tokenizer fallback paragraph. " * 200),
                    "trans_content": "",
                }
            ]

            self.parser._merge_short_sections(min_tokens=50)
            self.parser._chunk_long_sections(max_tokens=100)

            self.assertTrue(len(self.parser.sections_json) >= 1)
            self.assertTrue(all("chunk_token_count" in chunk for chunk in self.parser.sections_json))
        finally:
            parser_module.tiktoken.get_encoding = original_get_encoding

if __name__ == '__main__':
    unittest.main()
