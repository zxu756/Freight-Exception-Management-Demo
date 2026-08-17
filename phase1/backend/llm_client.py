"""
DeepSeek LLM client for AI conversation and diagnosis enhancement.
DeepSeek LLM 客户端 - AI 对话与诊断增强

DeepSeek exposes an OpenAI-compatible chat-completions endpoint. The client is
a thin wrapper using requests (no extra SDK dependency). When no API key is
configured it degrades gracefully (returns None), so the system keeps working
without an LLM.
"""
import requests

from config import settings


def is_available():
    """Return True if an LLM API key is configured."""
    return bool(settings.llm_api_key) and settings.llm_enabled


def chat(system_prompt, user_prompt, temperature=0.3, max_tokens=500):
    """
    Call DeepSeek chat completion.

    Returns:
        Assistant text, or None if LLM is unavailable / errors.
    """
    if not is_available():
        return None
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        print(f"[llm] request error: {e}")
    return None


# 系统提示：让 LLM 以货运异常协调专家身份回答
SYSTEM_PROMPT = (
    "You are an expert freight exception coordinator for Southern Freight, a New Zealand "
    "third-party logistics provider. Answer concisely in plain English (or Chinese if the "
    "user writes in Chinese). Focus on root cause, customer impact and practical recovery. "
    "Be specific and avoid generic filler."
)


def enhance_diagnosis(exception_type, root_cause, fallback):
    """Re-diagnose an out-of-distribution exception with the LLM.

    Falls back to the template diagnosis if the LLM is unavailable.
    """
    if not is_available():
        return fallback
    result = chat(
        SYSTEM_PROMPT,
        f"Diagnose this freight exception (detected type '{exception_type}'): \"{root_cause}\". "
        f"Give the likely root cause and the downstream impact in 1-2 concise sentences.",
        max_tokens=200,
    )
    return result or fallback


def polish_notification(fallback):
    """Polish a template customer notification into more natural language."""
    if not is_available():
        return fallback
    result = chat(
        SYSTEM_PROMPT,
        f"Rewrite this customer notification in a more natural, empathetic but professional "
        f"tone. Keep all the key facts (freight, cause, revised ETA, action, next update):\n\n"
        f"{fallback}",
        max_tokens=300,
    )
    return result or fallback
