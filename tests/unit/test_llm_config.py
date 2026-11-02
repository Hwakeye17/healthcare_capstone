
import os
import unittest
from unittest.mock import patch

from practo_agent.config.llm import (
    GROQ_BASE_URL,
    create_crewai_llm,
    get_llm_config,
)


class TestLLMConfig(unittest.TestCase):

    def test_default_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            config = get_llm_config()

        self.assertTrue(config["mock_mode"])
        self.assertEqual(config["provider"], "groq")
        self.assertEqual(
            config["model"],
            "openai/gpt-oss-120b",
        )
        self.assertEqual(config["temperature"], 0.0)

    def test_environment_overrides(self):
        with patch.dict(
            os.environ,
            {
                "MOCK_LLM": "false",
                "GROQ_MODEL": "custom-model",
                "GROQ_TEMPERATURE": "0.2",
            },
            clear=True,
        ):
            config = get_llm_config()

        self.assertFalse(config["mock_mode"])
        self.assertEqual(config["model"], "custom-model")
        self.assertEqual(config["temperature"], 0.2)

    def test_mock_mode_is_case_insensitive(self):
        with patch.dict(
            os.environ,
            {"MOCK_LLM": "TRUE"},
            clear=True,
        ):
            config = get_llm_config()

        self.assertTrue(config["mock_mode"])

    def test_missing_api_key_raises_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                ValueError,
                "GROQ_API_KEY",
            ):
                create_crewai_llm()

    @patch("crewai.LLM")
    def test_creates_native_crewai_llm(self, mock_llm):
        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "test-key",
                "GROQ_MODEL": "openai/gpt-oss-120b",
                "GROQ_TEMPERATURE": "0",
            },
            clear=True,
        ):
            create_crewai_llm()

        mock_llm.assert_called_once_with(
            model="openai/gpt-oss-120b",
            provider="openai",
            api_key="test-key",
            base_url=GROQ_BASE_URL,
            temperature=0.0,
        )


if __name__ == "__main__":
    unittest.main()
