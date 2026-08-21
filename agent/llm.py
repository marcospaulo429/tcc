"""Cliente LLM (vLLM OpenAI-compatible), temperature 0 + seed fixa por padrão."""
import time

from openai import OpenAI


class LLMClient:
    def __init__(self, base_url="http://127.0.0.1:8321/v1", model="Qwen/Qwen3-4B",
                 temperature=0.0, seed=1234, max_tokens=2048):
        self.client = OpenAI(base_url=base_url, api_key="EMPTY", timeout=180.0)
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens

    def config(self) -> dict:
        return {"model": self.model, "temperature": self.temperature,
                "seed": self.seed, "max_tokens": self.max_tokens}

    def chat(self, messages: list[dict]) -> dict:
        t0 = time.monotonic()
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages,
            temperature=self.temperature, seed=self.seed, max_tokens=self.max_tokens,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        return {
            "text": resp.choices[0].message.content or "",
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "wall_time_s": time.monotonic() - t0,
        }
