"""Slack thinking-steps card: full tool-call record + no-truncation answers.

Two behaviors are covered:

1. Per-tool rows + pagination — every tool call becomes its own ``tool-{n}``
   row; when a card fills (``_MAX_TOOLS_PER_CARD``) the next tool rolls onto a
   fresh plan card, so the complete record paginates across cards instead of
   being folded/capped into one row.

2. Long answers are not truncated — the card body is capped at Slack's
   streamed-markdown limit; an answer past it spills into follow-up cards
   (startStream → stopStream) so no content is lost.
"""

from __future__ import annotations

import pytest

from gateway.platforms import slack as slack_mod
from gateway.platforms.slack import (
    _CARD_BODY_LIMIT,
    SlackAdapter,
    _ThinkingCardState,
)


class FakeClient:
    def __init__(self) -> None:
        self.starts: list[dict] = []
        self.appends: list[dict] = []
        self.stops: list[dict] = []
        self.posts: list[dict] = []

    async def chat_startStream(self, **kwargs):
        self.starts.append(kwargs)
        return {"ok": True, "ts": f"card-{len(self.starts)}"}

    async def chat_appendStream(self, **kwargs):
        self.appends.append(kwargs)
        return {"ok": True}

    async def chat_stopStream(self, **kwargs):
        self.stops.append(kwargs)
        return {"ok": True}

    async def chat_postMessage(self, **kwargs):
        self.posts.append(kwargs)
        return {"ok": True, "ts": f"post-{len(self.posts)}"}

    # --- helpers --------------------------------------------------------
    def _all_chunks(self, calls: list[dict]) -> list[dict]:
        return [c for call in calls for c in (call.get("chunks") or [])]

    def task_updates(self) -> list[dict]:
        """Every task_update chunk across start/append/stop, in order."""
        out = []
        for call in (*self.starts, *self.appends, *self.stops):
            for c in call.get("chunks") or []:
                if c.get("type") == "task_update":
                    out.append(c)
        return out

    def appended_markdown(self) -> str:
        return "".join(
            c["text"]
            for c in self._all_chunks(self.appends)
            if c.get("type") == "markdown_text"
        )

    def stop_markdown(self) -> str:
        return "".join(
            c["text"]
            for c in self._all_chunks(self.stops)
            if c.get("type") == "markdown_text"
        )


def _adapter(client: FakeClient) -> SlackAdapter:
    adapter = SlackAdapter.__new__(SlackAdapter)
    adapter._thinking_cards = {}
    adapter._bot_message_ts = set()
    adapter._get_client = lambda chat_id: client  # type: ignore[method-assign]
    return adapter


def _register_card(adapter: SlackAdapter, channel: str, thread: str) -> _ThinkingCardState:
    # team_id/user_id present so continuation/pagination cards can open in a channel.
    state = _ThinkingCardState(
        card_ts=f"card-{thread}",
        channel_id=channel,
        thread_ts=thread,
        team_id="T1",
        user_id="U1",
    )
    adapter._thinking_cards[(channel, thread)] = state
    return state


# ───────────────────────────── tool rows ──────────────────────────────


@pytest.mark.asyncio
async def test_each_tool_call_gets_its_own_row() -> None:
    client = FakeClient()
    adapter = _adapter(client)
    state = _register_card(adapter, "C1", "t1")

    for i in range(3):
        ok = await adapter.record_tool_call("C1", "t1", tool_name="Shell", args={"command": f"cmd {i}"})
        assert ok is True

    in_progress = [c for c in client.task_updates()
                   if str(c["id"]).startswith("tool-") and c["status"] == "in_progress"]
    assert [c["id"] for c in in_progress] == ["tool-1", "tool-2", "tool-3"]
    # Distinct rows, not folded into one "tools" task.
    assert all(c["id"] != "tools" for c in client.task_updates())
    # First tool completed the analyze row; last tool stays in_progress.
    assert state.analyze_done is True
    assert state.active_tool_id == "tool-3"
    assert state.tool_seq == 3


@pytest.mark.asyncio
async def test_tool_rows_paginate_onto_new_cards_when_full(monkeypatch) -> None:
    monkeypatch.setattr(slack_mod, "_MAX_TOOLS_PER_CARD", 3)
    client = FakeClient()
    adapter = _adapter(client)
    state = _register_card(adapter, "C1", "t1")

    for i in range(7):
        ok = await adapter.record_tool_call("C1", "t1", tool_name="Shell", args={"command": f"cmd {i}"})
        assert ok is True

    # 3 rows/card → card0: 1-3, card1: 4-6, card2: 7  ⇒ 2 continuation cards opened.
    assert len(client.starts) == 2
    assert all(s.get("task_display_mode") == "plan" for s in client.starts)
    assert all(s["thread_ts"] == "t1" for s in client.starts)
    # Full record preserved: every tool is its own sequential row.
    in_progress = [c for c in client.task_updates()
                   if str(c["id"]).startswith("tool-") and c["status"] == "in_progress"]
    assert [c["id"] for c in in_progress] == [f"tool-{n}" for n in range(1, 8)]
    assert state.tool_seq == 7
    # The current card is the latest one (rolled twice).
    assert state.card_ts == "card-2"
    assert state.tools_on_card == 1


@pytest.mark.asyncio
async def test_finalize_completes_last_tool_and_respond() -> None:
    client = FakeClient()
    adapter = _adapter(client)
    _register_card(adapter, "C1", "t1")

    await adapter.record_tool_call("C1", "t1", tool_name="Read", args={"path": "/x.py"})
    ok = await adapter.finalize_thinking_card("C1", "t1", summary="done")

    assert ok is True
    finals = {(c["id"], c["status"]) for c in client.task_updates()}
    assert ("analyze", "complete") in finals
    assert ("tool-1", "complete") in finals  # the running tool is closed
    assert ("respond", "complete") in finals


# ─────────────────────────── answer body ──────────────────────────────


@pytest.mark.asyncio
async def test_short_response_stays_in_card() -> None:
    client = FakeClient()
    adapter = _adapter(client)
    state = _register_card(adapter, "C1", "t1")

    ok = await adapter.append_thinking_text("C1", "t1", "hello world", is_response=True)

    assert ok is True
    assert state.streamed_full_response is True
    assert client.appended_markdown() == "hello world"
    assert client.starts == []  # no continuation cards
    assert client.posts == []
    # The respond row was advanced to in_progress.
    assert ("respond", "in_progress") in {(c["id"], c["status"]) for c in client.task_updates()}


@pytest.mark.asyncio
async def test_long_response_paginates_into_cards() -> None:
    client = FakeClient()
    adapter = _adapter(client)
    _register_card(adapter, "C1", "t1")

    body = "A" * 25000  # > 11k cap → splits across cards
    ok = await adapter.append_thinking_text("C1", "t1", body, is_response=True)

    assert ok is True
    head = client.appended_markdown()
    assert len(head) <= _CARD_BODY_LIMIT
    # Remainder spills into follow-up streamed cards, not plain replies.
    assert len(client.starts) >= 1
    assert client.posts == []
    assert all(s["thread_ts"] == "t1" for s in client.starts)
    # No content lost across the first card + continuation cards.
    assert head.count("A") + client.stop_markdown().count("A") == 25000


@pytest.mark.asyncio
async def test_finalize_short_summary_no_overflow() -> None:
    client = FakeClient()
    adapter = _adapter(client)
    _register_card(adapter, "C1", "t2")

    ok = await adapter.finalize_thinking_card("C1", "t2", summary="all done")

    assert ok is True
    assert len(client.stops) == 1
    assert client.stop_markdown() == "all done"
    assert client.starts == []
    assert client.posts == []


@pytest.mark.asyncio
async def test_finalize_long_summary_paginates_into_cards() -> None:
    client = FakeClient()
    adapter = _adapter(client)
    _register_card(adapter, "C1", "t2")

    summary = "B" * 25000
    ok = await adapter.finalize_thinking_card("C1", "t2", summary=summary)

    assert ok is True
    assert len(client.starts) >= 1  # continuation cards opened
    assert client.posts == []
    assert client.stop_markdown().count("B") == 25000  # nothing lost
