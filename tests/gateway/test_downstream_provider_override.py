import textwrap

import gateway.run as grun


def test_inference_provider_env_override_is_forwarded(tmp_path, monkeypatch):
    """The managed gateway provider override reaches runtime resolution."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    def write_cfg(body):
        (tmp_path / "config.yaml").write_text(textwrap.dedent(body))
    write_cfg(
        """
        model:
          default: test-model
          provider: configured-provider
        """
    )
    monkeypatch.setenv("HERMES_INFERENCE_PROVIDER", "service-provider")

    seen = {}

    def fake_resolve_runtime_provider(*, requested=None, **_kwargs):
        seen["requested"] = requested
        return {
            "provider": requested,
            "requested_provider": requested,
            "api_key": "test-key",
            "base_url": "https://example.invalid/v1",
            "api_mode": "chat_completions",
            "command": None,
            "args": [],
            "credential_pool": None,
        }

    monkeypatch.setattr(
        "hermes_cli.runtime_provider.resolve_runtime_provider",
        fake_resolve_runtime_provider,
    )

    kw = grun._resolve_runtime_agent_kwargs()

    assert seen["requested"] == "service-provider"
    assert kw["provider"] == "service-provider"
