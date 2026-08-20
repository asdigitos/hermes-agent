"""Behavior contract for the cron.allow_agent_scheduling config gate.

``_resolve_cron_disabled_toolsets`` decides which toolsets a cron-spawned
agent must never receive. Historically ``cronjob`` was hard-denied there as
loop-prevention policy. The ``cron.allow_agent_scheduling`` gate (config.yaml,
default off) makes that denial opt-out-able:

  - gate off / absent: byte-exact current behavior — ``cronjob`` denied.
  - agent-scheduling gate on: ``cronjob`` dropped from the base denylist.
  - agent-messaging gate on: ``messaging`` dropped from the base denylist so
    autonomous jobs that explicitly need outbound business messages can send.
  - ``clarify`` (requires a present user) and ``memory`` (cron agents run with
    skip_memory=True) remain denied regardless of either gate.
  - user-level ``agent.disabled_toolsets`` still layers on top, so a user who
    denies ``cronjob`` globally keeps it denied even with the gate on
    (per-job enabled_toolsets can never widen past the config denylist).
"""

import pytest

from cron.scheduler import _resolve_cron_disabled_toolsets


# The toolsets that must be denied in cron context no matter what either gate
# says: clarify requires a present user; memory is unbacked in cron runs.
ALWAYS_DISABLED = ["clarify", "memory"]


class TestGateOffDefault:
    def test_empty_config_denies_cronjob(self):
        assert _resolve_cron_disabled_toolsets({}) == [
            "cronjob", "messaging", "clarify", "memory",
        ]

    def test_none_config_denies_cronjob(self):
        assert _resolve_cron_disabled_toolsets(None) == [
            "cronjob", "messaging", "clarify", "memory",
        ]

    def test_cron_section_present_but_gate_absent(self):
        cfg = {"cron": {"preflight": True}}
        assert _resolve_cron_disabled_toolsets(cfg) == [
            "cronjob", "messaging", "clarify", "memory",
        ]

    def test_explicit_false_matches_default(self):
        cfg = {"cron": {"allow_agent_scheduling": False}}
        assert _resolve_cron_disabled_toolsets(cfg) == \
            _resolve_cron_disabled_toolsets({})

    @pytest.mark.parametrize("falsy", [False, None, "", 0])
    def test_falsy_values_keep_gate_off(self, falsy):
        cfg = {"cron": {"allow_agent_scheduling": falsy}}
        disabled = _resolve_cron_disabled_toolsets(cfg)
        assert "cronjob" in disabled


class TestGateOn:
    def test_cronjob_dropped_from_denylist(self):
        cfg = {"cron": {"allow_agent_scheduling": True}}
        disabled = _resolve_cron_disabled_toolsets(cfg)
        assert "cronjob" not in disabled

    def test_interactivity_and_memory_denials_survive_the_gate(self):
        cfg = {"cron": {"allow_agent_scheduling": True}}
        disabled = _resolve_cron_disabled_toolsets(cfg)
        for name in ALWAYS_DISABLED:
            assert name in disabled


class TestAgentMessagingGate:
    def test_messaging_is_denied_by_default(self):
        assert "messaging" in _resolve_cron_disabled_toolsets({})

    def test_explicit_gate_allows_messaging(self):
        cfg = {"cron": {"allow_agent_messaging": True}}
        disabled = _resolve_cron_disabled_toolsets(cfg)
        assert "messaging" not in disabled
        assert "cronjob" in disabled
        for name in ALWAYS_DISABLED:
            assert name in disabled

    def test_user_denylist_wins_over_messaging_gate(self):
        cfg = {
            "cron": {"allow_agent_messaging": True},
            "agent": {"disabled_toolsets": ["messaging"]},
        }
        assert "messaging" in _resolve_cron_disabled_toolsets(cfg)

    def test_user_denylist_wins_over_gate(self):
        # A user who denies cronjob in agent.disabled_toolsets keeps it
        # denied even with the gate on — the gate only removes the built-in
        # policy denial, never the user's own config denylist.
        cfg = {
            "cron": {"allow_agent_scheduling": True},
            "agent": {"disabled_toolsets": ["cronjob"]},
        }
        assert "cronjob" in _resolve_cron_disabled_toolsets(cfg)

    def test_unrelated_user_denylist_layers_without_reviving_cronjob(self):
        cfg = {
            "cron": {"allow_agent_scheduling": True},
            "agent": {"disabled_toolsets": ["browser"]},
        }
        disabled = _resolve_cron_disabled_toolsets(cfg)
        assert "browser" in disabled
        assert "cronjob" not in disabled


class TestUserLayerUnchanged:
    def test_user_denylist_still_layers_when_gate_off(self):
        cfg = {"agent": {"disabled_toolsets": ["browser", "cronjob"]}}
        disabled = _resolve_cron_disabled_toolsets(cfg)
        assert "browser" in disabled
        # No duplicate when the user names an already-denied toolset.
        assert disabled.count("cronjob") == 1

    def test_blank_and_whitespace_entries_ignored(self):
        cfg = {
            "cron": {"allow_agent_scheduling": True},
            "agent": {"disabled_toolsets": ["", "  ", "browser"]},
        }
        disabled = _resolve_cron_disabled_toolsets(cfg)
        assert "browser" in disabled
        assert "" not in disabled
