"""
Infer-mode smoke test for simple_token_burner_app after LiteLLM refactor.

Uses litellm's mock_response kwarg so no API key is required.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import litellm


@pytest.fixture(autouse=True)
def _mock_litellm_completion(monkeypatch):
    """Inject mock_response into every litellm.completion call."""
    _orig = litellm.completion

    def _patched(*args, **kwargs):
        kwargs["mock_response"] = "Paris is the capital of France."
        return _orig(*args, **kwargs)

    monkeypatch.setattr(litellm, "completion", _patched)
    # Disable LurkLogger registration so no DB is needed
    monkeypatch.setenv("SMART_LLM_DB_URL", "")


class TestLLMClientInfer:
    def test_execute_prompt_returns_response(self):
        from simple_token_burner_app.llm_client import LLMClient

        client = LLMClient(model="openai/gpt-4o-mini", burner_mode="infer")
        resp = client.execute_prompt(
            prompt="What is the capital of France?",
            max_tokens=50,
            root_id="small-01",
            category="small",
            system_prompt="Answer in one sentence.",
        )
        assert resp is not None
        assert resp.error is None
        assert "Paris" in resp.content

    def test_metadata_present_in_litellm_call(self, monkeypatch):
        """Verify that metadata kwarg is passed through to litellm.completion."""
        import litellm as _ll

        captured = {}
        _orig2 = _ll.completion

        def _spy(*args, **kwargs):
            captured["metadata"] = kwargs.get("metadata")
            return _orig2(*args, **kwargs)

        monkeypatch.setattr(_ll, "completion", _spy)

        from simple_token_burner_app.llm_client import LLMClient

        client = LLMClient(model="openai/gpt-4o-mini", burner_mode="infer")
        client.execute_prompt(
            prompt="Hello",
            max_tokens=10,
            root_id="small-02",
            category="small",
        )
        meta = captured.get("metadata", {})
        assert meta.get("template_id") == "small-02"
        assert meta.get("category") == "small"
        assert meta.get("intent") == "infer"
        assert "session_id" in meta


class TestAgentInfer:
    def test_agent_executes_single_prompt(self):
        from simple_token_burner_app.agent import SimpleAgent, AgentConfig

        config = AgentConfig(
            model="openai/gpt-4o-mini",
            categories=["small"],
            max_prompts=1,
            burner_mode="infer",
            enable_file_logging=False,
            enable_console_logging=False,
        )
        agent = SimpleAgent(config)
        agent.run()
        assert agent.prompts_executed >= 1
