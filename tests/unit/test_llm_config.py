
import os
import unittest
from unittest.mock import patch

from practo_agent.agents.mock_llm import MockCrewAILLM
from practo_agent.config.groq_llm import GroqReActLLM
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
            "qwen/qwen3.8-27b",
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

    def test_mock_mode_creates_offline_crewai_llm_without_api_key(self):
        with patch.dict(os.environ, {"MOCK_LLM": "true"}, clear=True):
            llm = create_crewai_llm(query="test query")
            telemetry_disabled = os.environ.get("OTEL_SDK_DISABLED")

        self.assertIsInstance(llm, MockCrewAILLM)
        self.assertEqual(llm.query, "test query")
        self.assertEqual(telemetry_disabled, "true")

    def test_missing_api_key_raises_error_when_mock_mode_is_disabled(self):
        with patch.dict(
            os.environ,
            {"MOCK_LLM": "false"},
            clear=True,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "GROQ_API_KEY",
            ):
                create_crewai_llm()

    def test_live_crewai_llm_uses_react_tool_execution(self):
        llm = GroqReActLLM(
            model="qwen/qwen3.8-27b",
            provider="openai",
            api_key="test-key",
            base_url=GROQ_BASE_URL,
            temperature=0.0,
        )

        self.assertFalse(llm.supports_function_calling())

    @patch("practo_agent.config.groq_llm.GroqReActLLM")
    def test_creates_groq_react_llm(self, mock_llm):
        with patch.dict(
            os.environ,
            {
                "GROQ_API_KEY": "test-key",
                "MOCK_LLM": "false",
                "GROQ_MODEL": "qwen/qwen3.8-27b",
                "GROQ_TEMPERATURE": "0",
            },
            clear=True,
        ):
            create_crewai_llm()

        mock_llm.assert_called_once_with(
            model="qwen/qwen3.8-27b",
            provider="openai",
            api_key="test-key",
            base_url=GROQ_BASE_URL,
            temperature=0.0,
            max_completion_tokens=1024,
        )


if __name__ == "__main__":
    unittest.main()
