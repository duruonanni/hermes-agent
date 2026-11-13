"""Feishu topic send must never use receive_id_type=thread_id (API 99992402).

``_send_raw_message`` used to pass the topic id as receive_id with
``receive_id_type="thread_id"`` when a reply anchor was missing. Feishu
rejects that field; the legal in-topic path is ``message.reply`` with
``reply_in_thread=True``. With no anchor, the message is posted to the
chat top-level and a warning is logged so the drop out of the topic is
not silent.
"""

from __future__ import annotations

import json
import logging
import sys
import types
from types import SimpleNamespace

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.feishu.adapter import FeishuAdapter

logger = logging.getLogger("plugins.platforms.feishu.adapter")

_THREAD_ID = "omt_topic_abc"
_CHAT_ID = "oc_main_chat"
_ANCHOR_ID = "om_anchor_1"
_LISTED_ID = "om_listed_1"
_PAYLOAD = '{"text":"hello"}'


class _FakeListMessageBuilder:
    def __init__(self):
        self._fields = {}

    def container_id_type(self, value):
        self._fields["container_id_type"] = value
        return self

    def container_id(self, value):
        self._fields["container_id"] = value
        return self

    def page_size(self, value):
        self._fields["page_size"] = value
        return self

    def build(self):
        return SimpleNamespace(**self._fields)


class _FakeListMessageRequest:
    @staticmethod
    def builder():
        return _FakeListMessageBuilder()


class _RecordingMessageAPI:
    def __init__(self, list_message_id=None, reply_fails=False, reply_code=None, create_fails=False):
        self.create_calls: list[object] = []
        self.reply_calls: list[object] = []
        self.list_calls: list[object] = []
        self.last_reply_response = None
        self.last_create_response = None
        self._list_message_id = list_message_id
        self._reply_fails = reply_fails or reply_code is not None
        self._reply_code = 99992402 if reply_code is None else reply_code
        self._create_fails = create_fails

    def create(self, request):
        self.create_calls.append(request)
        if self._create_fails:
            self.last_create_response = SimpleNamespace(
                success=lambda: False, code=99991668, msg="create failed",
            )
            return self.last_create_response
        self.last_create_response = SimpleNamespace(
            success=lambda: True, data=SimpleNamespace(message_id="om_created"),
        )
        return self.last_create_response

    def reply(self, request):
        self.reply_calls.append(request)
        if self._reply_fails:
            self.last_reply_response = SimpleNamespace(
                success=lambda: False, code=self._reply_code, msg="reply failed",
            )
            return self.last_reply_response
        self.last_reply_response = SimpleNamespace(
            success=lambda: True, data=SimpleNamespace(message_id="om_replied"),
        )
        return self.last_reply_response

    def list(self, request):
        self.list_calls.append(request)
        if self._list_message_id is None:
            return SimpleNamespace(success=lambda: True, data=SimpleNamespace(items=[]))
        return SimpleNamespace(
            success=lambda: True,
            data=SimpleNamespace(items=[SimpleNamespace(message_id=self._list_message_id)]),
        )


def _install_list_message_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_fetch_last_message_in_thread`` imports ListMessageRequest at call time."""
    try:
        from lark_oapi.api.im.v1 import ListMessageRequest  # noqa: F401
        return
    except ImportError:
        pass

    for parent in ("lark_oapi", "lark_oapi.api", "lark_oapi.api.im"):
        if parent not in sys.modules:
            monkeypatch.setitem(sys.modules, parent, types.ModuleType(parent))
    name = "lark_oapi.api.im.v1"
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setattr(mod, "ListMessageRequest", _FakeListMessageRequest, raising=False)


def _wired_adapter(
    monkeypatch: pytest.MonkeyPatch,
    *,
    list_message_id=None,
    reply_fails=False,
    reply_code=None,
    create_fails=False,
):
    _install_list_message_request(monkeypatch)
    adapter = FeishuAdapter(PlatformConfig())
    api = _RecordingMessageAPI(
        list_message_id=list_message_id,
        reply_fails=reply_fails,
        reply_code=reply_code,
        create_fails=create_fails,
    )
    file_api = SimpleNamespace(
        create=lambda request: SimpleNamespace(
            success=lambda: True, data=SimpleNamespace(file_key="fk_audio"),
        ),
    )
    adapter._client = SimpleNamespace(im=SimpleNamespace(v1=SimpleNamespace(message=api, file=file_api)))

    async def _passthrough(func, *args):
        return func(*args)

    monkeypatch.setattr(adapter, "_run_blocking", _passthrough)
    return adapter, api


def _reply_in_thread(request) -> object:
    body = getattr(request, "request_body", None) or getattr(request, "body", None)
    return getattr(body, "reply_in_thread", None)


def _receive_id_type(request) -> object:
    return getattr(request, "receive_id_type", None)


def _receive_id(request) -> object:
    body = getattr(request, "request_body", None) or getattr(request, "body", None)
    return getattr(body, "receive_id", None)


def _msg_type(request) -> object:
    body = getattr(request, "request_body", None) or getattr(request, "body", None)
    return getattr(body, "msg_type", None)


def _content(request) -> object:
    body = getattr(request, "request_body", None) or getattr(request, "body", None)
    return getattr(body, "content", None)


@pytest.mark.asyncio
async def test_thread_id_with_reply_to_uses_reply_and_skips_list(monkeypatch):
    adapter, api = _wired_adapter(monkeypatch, list_message_id=_LISTED_ID)

    await adapter._send_raw_message(
        chat_id=_CHAT_ID,
        msg_type="text",
        payload=_PAYLOAD,
        reply_to=_ANCHOR_ID,
        metadata={"thread_id": _THREAD_ID},
    )

    assert api.list_calls == []
    assert len(api.reply_calls) == 1
    assert api.create_calls == []
    assert _reply_in_thread(api.reply_calls[0]) is True
    assert getattr(api.reply_calls[0], "message_id", None) == _ANCHOR_ID


@pytest.mark.asyncio
async def test_thread_id_without_reply_to_lists_then_replies(monkeypatch):
    adapter, api = _wired_adapter(monkeypatch, list_message_id=_LISTED_ID)

    await adapter._send_raw_message(
        chat_id=_CHAT_ID,
        msg_type="text",
        payload=_PAYLOAD,
        reply_to=None,
        metadata={"thread_id": _THREAD_ID},
    )

    assert len(api.list_calls) == 1
    assert len(api.reply_calls) == 1
    assert api.create_calls == []
    assert _reply_in_thread(api.reply_calls[0]) is True
    assert getattr(api.reply_calls[0], "message_id", None) == _LISTED_ID


@pytest.mark.asyncio
async def test_thread_id_without_anchor_falls_back_to_chat_create(monkeypatch, caplog):
    adapter, api = _wired_adapter(monkeypatch, list_message_id=None)

    with caplog.at_level(logging.WARNING, logger=logger.name):
        await adapter._send_raw_message(
            chat_id=_CHAT_ID,
            msg_type="text",
            payload=_PAYLOAD,
            reply_to=None,
            metadata={"thread_id": _THREAD_ID},
        )

    assert len(api.list_calls) == 1
    assert api.reply_calls == []
    assert len(api.create_calls) == 1
    assert _receive_id_type(api.create_calls[0]) == "chat_id"
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings, "missing-anchor fallback must log a warning, not stay silent"
    joined = " ".join(r.getMessage() for r in warnings).lower()
    assert "topic" in joined and "not appear" in joined


_ROUTING_CASES = [
    pytest.param("oc_main_chat", "om_user", "omt_t", "om_listed", id="reply_to_present"),
    pytest.param("oc_main_chat", None, "omt_t", "om_listed", id="list_anchor_then_reply"),
    pytest.param("oc_main_chat", None, "omt_t", None, id="no_anchor_chat_id"),
    pytest.param("ou_user_1", None, "omt_t", None, id="no_anchor_open_id"),
    pytest.param("feishu_user_id:u_1", None, "omt_t", None, id="no_anchor_user_id"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("chat_id, reply_to, thread_id, list_message_id", _ROUTING_CASES)
async def test_create_receive_id_type_is_never_thread_id(
    monkeypatch, chat_id, reply_to, thread_id, list_message_id,
):
    adapter, api = _wired_adapter(monkeypatch, list_message_id=list_message_id)

    await adapter._send_raw_message(
        chat_id=chat_id,
        msg_type="text",
        payload=_PAYLOAD,
        reply_to=reply_to,
        metadata={"thread_id": thread_id},
    )

    assert all(_receive_id_type(req) != "thread_id" for req in api.create_calls)


@pytest.mark.asyncio
async def test_thread_id_reply_failure_falls_back_to_chat_create(monkeypatch, caplog):
    adapter, api = _wired_adapter(monkeypatch, reply_fails=True)

    with caplog.at_level(logging.WARNING, logger=logger.name):
        response = await adapter._send_raw_message(
            chat_id=_CHAT_ID,
            msg_type="text",
            payload=_PAYLOAD,
            reply_to=_ANCHOR_ID,
            metadata={"thread_id": _THREAD_ID},
        )

    result = adapter._finalize_send_result(response, "send failed")
    assert result.success is True
    assert len(api.reply_calls) == 1
    assert len(api.create_calls) == 1
    assert _receive_id_type(api.create_calls[0]) == "chat_id"
    assert _receive_id(api.create_calls[0]) == _CHAT_ID
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings, "reply-failure fallback must log a warning, not stay silent"
    joined = " ".join(r.getMessage() for r in warnings).lower()
    assert "reply" in joined and "failed" in joined
    assert "top-level" in joined


@pytest.mark.asyncio
async def test_uploaded_audio_in_topic_falls_back_to_chat_when_reply_fails(
    monkeypatch, tmp_path, caplog,
):
    adapter, api = _wired_adapter(
        monkeypatch, list_message_id=_LISTED_ID, reply_fails=True,
    )
    audio = tmp_path / "voice.ogg"
    audio.write_bytes(b"not-real-opus")

    with caplog.at_level(logging.WARNING, logger=logger.name):
        result = await adapter._send_uploaded_file_message(
            chat_id=_CHAT_ID,
            file_path=str(audio),
            reply_to=_ANCHOR_ID,
            metadata={"thread_id": _THREAD_ID},
            outbound_message_type="audio",
        )

    assert result.success is True
    assert len(api.reply_calls) == 1
    assert len(api.create_calls) == 1
    assert _receive_id_type(api.create_calls[0]) == "chat_id"
    assert _receive_id(api.create_calls[0]) == _CHAT_ID
    assert _msg_type(api.create_calls[0]) == "audio"
    payload = json.loads(_content(api.create_calls[0]))
    assert payload.get("file_key")


@pytest.mark.asyncio
async def test_thread_reply_withdrawn_code_does_not_fall_back_to_chat(monkeypatch):
    adapter, api = _wired_adapter(monkeypatch, reply_code=230011)

    response = await adapter._send_raw_message(
        chat_id=_CHAT_ID,
        msg_type="text",
        payload=_PAYLOAD,
        reply_to=_ANCHOR_ID,
        metadata={"thread_id": _THREAD_ID},
    )

    assert api.create_calls == []
    assert response is api.last_reply_response
    assert getattr(response, "code", None) == 230011
    assert not response.success()


@pytest.mark.asyncio
async def test_thread_reply_non_withdrawn_code_falls_back_to_chat(monkeypatch, caplog):
    adapter, api = _wired_adapter(monkeypatch, reply_code=99992402)

    with caplog.at_level(logging.WARNING, logger=logger.name):
        response = await adapter._send_raw_message(
            chat_id=_CHAT_ID,
            msg_type="text",
            payload=_PAYLOAD,
            reply_to=_ANCHOR_ID,
            metadata={"thread_id": _THREAD_ID},
        )

    result = adapter._finalize_send_result(response, "send failed")
    assert result.success is True
    assert len(api.reply_calls) == 1
    assert len(api.create_calls) == 1
    assert _receive_id_type(api.create_calls[0]) == "chat_id"
    assert response is api.last_create_response
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings, "non-withdrawn reply failure must log before falling back"
    joined = " ".join(r.getMessage() for r in warnings).lower()
    assert "reply" in joined and "failed" in joined
    assert "top-level" in joined


@pytest.mark.asyncio
async def test_thread_reply_fallback_returns_create_failure(monkeypatch):
    adapter, api = _wired_adapter(monkeypatch, reply_code=99992402, create_fails=True)

    response = await adapter._send_raw_message(
        chat_id=_CHAT_ID,
        msg_type="text",
        payload=_PAYLOAD,
        reply_to=_ANCHOR_ID,
        metadata={"thread_id": _THREAD_ID},
    )

    assert len(api.reply_calls) == 1
    assert len(api.create_calls) == 1
    assert response is api.last_create_response
    assert not response.success()
    result = adapter._finalize_send_result(response, "send failed")
    assert result.success is False
