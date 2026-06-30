import json
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import AzureOpenAI

from app.core.config import get_settings


class AzureLLM:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = AzureOpenAI(
            api_key=self.settings.azure_openai_api_key,
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_version=self.settings.azure_openai_api_version,
        )

    def _is_reasoning_model(self) -> bool:
        deployment = self.settings.azure_openai_chat_deployment.lower()
        reasoning_prefixes = (
            "gpt-5",
            "o1",
            "o3",
            "o4",
        )
        return deployment.startswith(reasoning_prefixes)

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = self.client.embeddings.create(
            model=self.settings.azure_openai_embedding_deployment,
            input=texts,
        )

        return [item.embedding for item in response.data]

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def chat_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        request = {
            "model": self.settings.azure_openai_chat_deployment,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        if not self._is_reasoning_model():
            request["temperature"] = temperature

        response = self.client.chat.completions.create(**request)

        return response.choices[0].message.content or ""

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        request = {
            "model": self.settings.azure_openai_chat_deployment,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        if not self._is_reasoning_model():
            request["temperature"] = temperature

        response = self.client.chat.completions.create(**request)

        text = response.choices[0].message.content or "{}"

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "error": "invalid_json",
                "raw": text,
            }
