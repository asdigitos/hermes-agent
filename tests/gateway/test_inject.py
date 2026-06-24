from types import SimpleNamespace
from unittest.mock import AsyncMock
import os
import stat

import pytest

from gateway.config import GatewayConfig, Platform
from gateway.inject import validate_socket_security
from gateway.platforms.base import SendResult
from gateway.run import GatewayRunner


def _make_runner(adapter=None):
    runner = GatewayRunner.__new__(GatewayRunner)
    runner.config = GatewayConfig()
    runner.adapters = {}
    runner.session_store = None
    if adapter is not None:
        runner.adapters[Platform.SLACK] = adapter
    return runner


@pytest.mark.asyncio
async def test_inject_local_message_routes_through_handler_and_thread():
    adapter = SimpleNamespace(send=AsyncMock(return_value=SendResult(success=True, message_id="bot-ts")))
    runner = _make_runner(adapter)
    seen = {}

    async def fake_handle(event):
        seen["event"] = event
        return "agent response"

    runner._handle_message = fake_handle

    result = await runner.inject_local_message(
        {
            "platform": "slack",
            "chat_id": "C123",
            "thread_id": "171.1",
            "text": "local prompt",
        }
    )

    assert result["ok"] is True
    assert result["delivered"] is True
    assert result["session_key"] == "agent:main:slack:channel:C123:171.1"
    event = seen["event"]
    assert event.internal is True
    assert event.text == "local prompt"
    assert event.source.platform == Platform.SLACK
    assert event.source.chat_id == "C123"
    assert event.source.thread_id == "171.1"
    adapter.send.assert_awaited_once_with(
        "C123",
        "agent response",
        metadata={"thread_id": "171.1"},
    )


@pytest.mark.asyncio
async def test_inject_local_message_rejects_unconnected_platform():
    runner = _make_runner()
    result = await runner.inject_local_message(
        {
            "platform": "slack",
            "chat_id": "C123",
            "thread_id": "171.1",
            "text": "local prompt",
        }
    )

    assert result == {"ok": False, "error": "platform is not connected: slack"}


@pytest.mark.asyncio
async def test_inject_local_message_reports_send_failure():
    adapter = SimpleNamespace(send=AsyncMock(return_value=SendResult(success=False, error="denied")))
    runner = _make_runner(adapter)
    runner._handle_message = AsyncMock(return_value="agent response")

    result = await runner.inject_local_message(
        {
            "platform": "slack",
            "chat_id": "C123",
            "thread_id": "171.1",
            "text": "local prompt",
        }
    )

    assert result == {"ok": False, "error": "denied", "response": "agent response"}


def test_validate_socket_security_rejects_public_socket():
    class FakeSocketPath:
        def stat(self):
            return SimpleNamespace(st_mode=stat.S_IFSOCK | 0o666, st_uid=os.getuid())

    ok, reason = validate_socket_security(FakeSocketPath())

    assert ok is False
    assert "permissions are too broad" in reason
