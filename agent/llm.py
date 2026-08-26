"""Cliente LLM (vLLM OpenAI-compatible), temperature 0 + seed fixa por padrão.

O modelo pode ser trocado via env var TCC_MODEL (usado no D2c, Qwen3-1.7B).
TCC_MERGE_ROLES=1 funde mensagens consecutivas do mesmo role (templates com
alternância estrita, ex. Mistral — adendo 35a); paths Qwen não usam.
"""
import os
import time

from openai import OpenAI


def _merge_roles(messages: list[dict]) -> list[dict]:
    out: list[dict] = []
    for m in messages:
        if out and out[-1]["role"] == m["role"]:
            out[-1] = {"role": m["role"],
                       "content": out[-1]["content"] + "\n\n" + m["content"]}
        else:
            out.append(dict(m))
    return out


class LLMClient:
    def __init__(self, base_url="http://127.0.0.1:8321/v1", model=None,
                 temperature=0.0, seed=1234, max_tokens=2048):
        self.client = OpenAI(base_url=base_url, api_key="EMPTY", timeout=180.0)
        self.model = model or os.environ.get("TCC_MODEL", "Qwen/Qwen3-4B")
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens

    def config(self) -> dict:
        return {"model": self.model, "temperature": self.temperature,
                "seed": self.seed, "max_tokens": self.max_tokens}

    def chat(self, messages: list[dict], *, temperature=None, seed=None,
             max_tokens=None) -> dict:
        """Overrides por chamada (None = default da instância) p/ amostragem de a′."""
        t0 = time.monotonic()
        if os.environ.get("TCC_MERGE_ROLES"):
            messages = _merge_roles(messages)
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages,
            temperature=self.temperature if temperature is None else temperature,
            seed=self.seed if seed is None else seed,
            max_tokens=self.max_tokens if max_tokens is None else max_tokens,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        return {
            "text": resp.choices[0].message.content or "",
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "wall_time_s": time.monotonic() - t0,
            "finish_reason": resp.choices[0].finish_reason,
        }
