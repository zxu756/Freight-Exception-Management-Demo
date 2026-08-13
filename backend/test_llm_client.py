"""
Unit tests for the DeepSeek LLM client (graceful degradation without an API key).
LLM 客户端降级逻辑单元测试
"""
import llm_client


def test_not_available_without_key(monkeypatch):
    """Without an API key, the LLM is unavailable."""
    monkeypatch.setattr(llm_client.settings, "llm_api_key", "")
    monkeypatch.setattr(llm_client.settings, "llm_enabled", True)
    assert llm_client.is_available() is False


def test_chat_returns_none_without_key(monkeypatch):
    """chat() returns None when no key is configured."""
    monkeypatch.setattr(llm_client.settings, "llm_api_key", "")
    assert llm_client.chat("sys", "user") is None


def test_enhance_diagnosis_falls_back_without_key(monkeypatch):
    """enhance_diagnosis returns the fallback when the LLM is unavailable."""
    monkeypatch.setattr(llm_client.settings, "llm_api_key", "")
    result = llm_client.enhance_diagnosis("delay", "vessel delayed", "template diagnosis")
    assert result == "template diagnosis"


def test_polish_notification_falls_back_without_key(monkeypatch):
    """polish_notification returns the fallback when the LLM is unavailable."""
    monkeypatch.setattr(llm_client.settings, "llm_api_key", "")
    result = llm_client.polish_notification("template notification")
    assert result == "template notification"
