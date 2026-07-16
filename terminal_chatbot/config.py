from .providers.local import LocalProvider
from .providers.http import HTTPProvider

PROVIDERS = {
    "opencode": {
        "label": "OpenCode Zen (free models)",
        "base_url": "https://opencode.ai/zen/v1",
        "env_key": "OPENCODE_API_KEY",
        "models": [
            "hy3-free",
            "deepseek-v4-flash-free",
            "mimo-v2.5-free",
            "north-mini-code-free",
            "nemotron-3-ultra-free",
            "big-pickle",
        ],
        "default_model": "hy3-free",
        "free": True,
    },
}


def list_providers():
    rows = []
    for pid, spec in PROVIDERS.items():
        tag = "free" if spec.get("free") else "key"
        rows.append((pid, spec["label"], spec["default_model"], tag))
    return rows


def build_provider(provider_id, model=None, api_key=None):
    if provider_id == "local":
        return LocalProvider()

    if provider_id not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider_id}'. Choices: local, " + ", ".join(PROVIDERS))

    spec = PROVIDERS[provider_id]
    model = model or spec["default_model"]
    api_key = api_key or __import__("os").environ.get(spec["env_key"])

    return HTTPProvider(
        id=provider_id,
        label=spec["label"],
        base_url=spec["base_url"],
        api_key=api_key,
        model=model,
        env_key=spec["env_key"],
    )
