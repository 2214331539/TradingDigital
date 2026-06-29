import os
from collections.abc import AsyncGenerator, Iterable
from functools import lru_cache
from typing import Optional

from dotenv import dotenv_values, find_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from tradedigital.apps.llm.domain.models import LlmModel, Message


class ModelGatewayError(RuntimeError):
    pass


@lru_cache
def local_env_values() -> dict:
    env_file = find_dotenv(usecwd=True)
    return dict(dotenv_values(env_file)) if env_file else {}


def get_api_key(api_key_ref: str) -> Optional[str]:
    return os.getenv(api_key_ref) or local_env_values().get(api_key_ref)


def build_context(
    messages: Iterable[Message],
    new_content: str,
    system_prompt: Optional[str] = None,
) -> list[dict[str, str]]:
    history = [
        {"role": message.role, "content": message.content}
        for message in messages
        if message.role in {"user", "assistant"} and not message.deleted_at
    ]
    history.append({"role": "user", "content": new_content})
    # Keep the most recent turns, but never drop the assistant preset's system
    # prompt — it is prepended after the window is applied.
    history = history[-20:]
    if system_prompt and system_prompt.strip():
        return [{"role": "system", "content": system_prompt}, *history]
    return history


async def openai_compatible_stream(
    model: LlmModel, messages: list[dict[str, str]]
) -> AsyncGenerator[str, None]:
    api_key = get_api_key(model.api_key_ref)
    if not api_key:
        raise ModelGatewayError(f"模型 API Key 未配置：请设置环境变量 {model.api_key_ref}")

    client = AsyncOpenAI(base_url=model.base_url.rstrip("/"), api_key=api_key, timeout=60)
    request_payload = {
        "model": model.model_key,
        "messages": messages,
        "temperature": float(model.default_temperature),
        "max_tokens": model.max_output_tokens,
    }

    try:
        if model.support_streaming:
            stream = await client.chat.completions.create(**request_payload, stream=True)
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
            return

        completion = await client.chat.completions.create(**request_payload)
        if completion.choices:
            content = completion.choices[0].message.content
            if isinstance(content, str) and content:
                yield content
                return
        raise ModelGatewayError("模型未返回内容")
    except APIStatusError as exc:
        raise ModelGatewayError(f"模型接口返回错误：HTTP {exc.status_code}") from exc
    except APITimeoutError as exc:
        raise ModelGatewayError("模型接口请求超时") from exc
    except APIConnectionError as exc:
        raise ModelGatewayError("模型接口连接失败") from exc


async def stream_model_response(
    model: LlmModel, messages: list[dict[str, str]]
) -> AsyncGenerator[str, None]:
    if model.provider_code not in {"openai", "openai_compatible"}:
        raise ModelGatewayError(f"暂不支持的模型供应商：{model.provider_code}")
    async for chunk in openai_compatible_stream(model, messages):
        yield chunk
