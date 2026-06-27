import json
import os
from typing import AsyncGenerator, Dict, Iterable, List

import httpx

from app.db.models import AiModel, Message


class ModelGatewayError(RuntimeError):
    pass


def build_context(messages: Iterable[Message], new_content: str) -> List[Dict[str, str]]:
    context = [
        {"role": message.role, "content": message.content}
        for message in messages
        if message.role in {"user", "assistant"} and not message.deleted_at
    ]
    context.append({"role": "user", "content": new_content})
    return context[-20:]


async def openai_compatible_stream(
    model: AiModel, messages: List[Dict[str, str]]
) -> AsyncGenerator[str, None]:
    api_key = os.getenv(model.api_key_ref)
    if not api_key:
        raise ModelGatewayError(f"模型 API Key 未配置：请设置环境变量 {model.api_key_ref}")

    url = model.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model.model_key,
        "messages": messages,
        "stream": True,
        "temperature": float(model.default_temperature),
        "max_tokens": model.max_output_tokens,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line.removeprefix("data:").strip()
                if raw == "[DONE]":
                    break
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                delta = event.get("choices", [{}])[0].get("delta", {})
                if delta.get("content"):
                    yield delta["content"]


async def stream_model_response(
    model: AiModel, messages: List[Dict[str, str]]
) -> AsyncGenerator[str, None]:
    if model.provider not in {"openai", "openai_compatible"}:
        raise ModelGatewayError(f"暂不支持的模型供应商：{model.provider}")

    async for chunk in openai_compatible_stream(model, messages):
        yield chunk
