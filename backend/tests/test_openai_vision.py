"""이슈 02 — OpenAIVisionClient: 이미지 배선 + 사용량 추적 (openai mock)."""
import types

from apps.agent import openai_client
from apps.agent.openai_client import OpenAIVisionClient, get_usage, reset_usage


class _FakeResp:
    def __init__(self):
        msg = types.SimpleNamespace(content='{"attributes":[{"name":"material","value":"glass"}]}')
        self.choices = [types.SimpleNamespace(message=msg)]
        self.usage = types.SimpleNamespace(prompt_tokens=100, completion_tokens=20)


class _FakeClient:
    def __init__(self):
        self.captured = None
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create)
        )

    async def _create(self, **kwargs):
        self.captured = kwargs
        return _FakeResp()


async def test_vision_client_wires_images_and_tracks_usage(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(openai_client, "_client", lambda: fake)
    reset_usage()

    out = await OpenAIVisionClient(model="gpt-4o").extract(
        ["http://a.jpg", "http://b.jpg"], "extract specs"
    )
    assert '"material"' in out

    # 이미지 URL이 image_url 파트로 전달됨
    content = fake.captured["messages"][0]["content"]
    image_urls = [c["image_url"]["url"] for c in content if c["type"] == "image_url"]
    assert image_urls == ["http://a.jpg", "http://b.jpg"]

    # 사용량 누적
    usage = get_usage()
    assert usage["chat_in"] == 100
    assert usage["chat_out"] == 20
