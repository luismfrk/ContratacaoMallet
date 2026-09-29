import unittest
from unittest.mock import Mock

from ai.service import AIConfigurationError, AIProviderError, AIService, redact_sensitive_data


class TestAIService(unittest.TestCase):
    def test_exige_configuracao(self) -> None:
        service = AIService(env={"AI_PROVIDER": "disabled"})
        with self.assertRaises(AIConfigurationError):
            service.suggest("DFD", "Justificativa", "", {})

    def test_redige_com_contexto_sanitizado(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": [{"message": {"content": "  Sugestão segura.  "}}]}
        session = Mock()
        session.post.return_value = response
        service = AIService(session=session, env={
            "AI_PROVIDER": "aimlapi", "AI_API_KEY": "segredo", "AI_MODEL": "modelo-teste"
        })

        result = service.suggest("DFD", "Justificativa", "Texto", {"contato": "teste@exemplo.com"})

        self.assertEqual(result, "Sugestão segura.")
        request = session.post.call_args
        self.assertEqual(request.kwargs["json"]["model"], "modelo-teste")
        self.assertNotIn("teste@exemplo.com", str(request.kwargs["json"]))
        self.assertNotIn("segredo", str(request.kwargs["json"]))

    def test_converte_resposta_invalida_em_erro_amigavel(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {}
        session = Mock()
        session.post.return_value = response
        service = AIService(session=session, env={"AI_PROVIDER": "aimlapi", "AI_API_KEY": "x"})
        with self.assertRaises(AIProviderError):
            service.suggest("ETP", "Resultados", "", {})

    def test_remove_cpf_cnpj_e_email(self) -> None:
        sanitized = redact_sensitive_data("CPF 123.456.789-00 e a@b.com")
        self.assertNotIn("123.456.789-00", sanitized)
        self.assertNotIn("a@b.com", sanitized)

    def test_transforms_example(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": [{"message": {"content": "Documento adaptado"}}]}
        session = Mock()
        session.post.return_value = response
        service = AIService(session=session, env={"AI_PROVIDER": "aimlapi", "AI_API_KEY": "x"})
        self.assertEqual(service.transform_example("Modelo", "Troque o objeto"), "Documento adaptado")

    def test_uses_groq_endpoint_and_default_model(self) -> None:
        service = AIService(env={"AI_PROVIDER": "groq", "AI_API_KEY": "gsk_teste"})
        self.assertTrue(service.enabled)
        self.assertEqual(service.endpoint, "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(service.model, "openai/gpt-oss-120b")


if __name__ == "__main__":
    unittest.main()
