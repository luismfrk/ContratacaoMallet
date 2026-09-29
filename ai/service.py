from __future__ import annotations

import os
import re
from typing import Any

import requests


class AIConfigurationError(RuntimeError):
    pass


class AIProviderError(RuntimeError):
    pass


_CPF_CNPJ = re.compile(r"(?<!\d)(?:\d[.\-/ ]*){11,14}(?!\d)")
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)


def redact_sensitive_data(value: str) -> str:
    """Remove identificadores que não são necessários para redigir sugestões."""
    value = _CPF_CNPJ.sub("[DOCUMENTO REMOVIDO]", value)
    return _EMAIL.sub("[E-MAIL REMOVIDO]", value)


def provider_error_message(exc: Exception, provider_name: str) -> str:
    response = getattr(exc, "response", None)
    if response is not None and response.status_code == 403:
        return f"A {provider_name} recusou a chamada. Verifique o saldo, limites e permissões da conta."
    return "O serviço de IA não respondeu corretamente. Tente novamente em instantes."


class AIService:
    providers = {
        "aimlapi": {
            "endpoint": "https://api.aimlapi.com/v1/chat/completions",
            "default_model": "openai/gpt-5-5",
            "name": "AIMLAPI",
        },
        "groq": {
            "endpoint": "https://api.groq.com/openai/v1/chat/completions",
            "default_model": "openai/gpt-oss-120b",
            "name": "Groq",
        },
    }

    def __init__(self, session: Any = requests, env: dict[str, str] | None = None) -> None:
        config = os.environ if env is None else env
        self.provider = config.get("AI_PROVIDER", "disabled").strip().lower()
        provider_config = self.providers.get(self.provider, {})
        self.endpoint = provider_config.get("endpoint", "")
        self.provider_name = provider_config.get("name", self.provider or "provedor")
        self.api_key = config.get("AI_API_KEY", "").strip()
        default_model = provider_config.get("default_model", "")
        self.model = config.get("AI_MODEL", default_model).strip() or default_model
        self.timeout = float(config.get("AI_TIMEOUT_SECONDS", "45"))
        self.session = session

    @property
    def enabled(self) -> bool:
        return self.provider in self.providers and bool(self.api_key) and bool(self.model)

    def suggest(self, document_type: str, field: str, current_text: str,
                context: dict[str, Any]) -> str:
        if not self.enabled:
            raise AIConfigurationError(
                "A assistência por IA ainda não foi configurada no servidor."
            )

        safe_context = {
            str(key)[:80]: redact_sensitive_data(str(value))[:2000]
            for key, value in context.items()
            if value not in (None, "", [], {})
        }
        prompt = (
            f"Documento: {document_type}. Campo: {field}.\n"
            f"Texto atual: {redact_sensitive_data(current_text)[:6000] or '[vazio]'}.\n"
            f"Contexto confirmado pelo usuário: {safe_context}.\n\n"
            "Redija somente uma sugestão para o campo indicado, em português do Brasil, "
            "com linguagem clara, objetiva e adequada a uma contratação pública municipal. "
            "Não invente fatos, valores, datas, fundamentos legais ou requisitos. Quando uma "
            "informação essencial não estiver no contexto, marque-a como [INFORMAR]. "
            "Não inclua introdução, comentários, título ou formatação Markdown."
        )
        try:
            response = self.session.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Você auxilia a redação de documentos de contratações "
                                "públicas. Preserve os fatos fornecidos e nunca os complete por suposição."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "max_completion_tokens": 1800,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            suggestion = payload["choices"][0]["message"]["content"].strip()
            if not suggestion:
                raise ValueError("resposta vazia")
            return suggestion
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError(provider_error_message(exc, self.provider_name)) from exc

    def transform_example(self, example_text: str, instruction: str) -> str:
        if not self.enabled:
            raise AIConfigurationError(
                "A assistência por IA ainda não foi configurada no servidor."
            )
        prompt = (
            "Use o documento de exemplo abaixo somente como referência de estrutura, tom e conteúdo. "
            "Aplique a alteração solicitada sem inventar fatos, valores, datas, pessoas ou fundamentos "
            "legais. Preserve o que não precisar ser alterado e marque informações ausentes como "
            "[INFORMAR]. Entregue apenas o texto final revisado, sem comentários nem Markdown.\n\n"
            f"ALTERAÇÃO SOLICITADA:\n{redact_sensitive_data(instruction)[:3000]}\n\n"
            f"DOCUMENTO DE EXEMPLO:\n{redact_sensitive_data(example_text)[:24000]}"
        )
        try:
            response = self.session.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Você revisa documentos de contratações públicas municipais com fidelidade ao material fornecido."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "max_completion_tokens": 6000,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip()
            if not result:
                raise ValueError("resposta vazia")
            return result
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError(provider_error_message(exc, self.provider_name)) from exc
