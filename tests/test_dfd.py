import unittest

from app import gerar_dfd, listar_tipos_dfd


def dados_validos() -> dict:
    return {
        "unidade_requisitante": "Secretaria Municipal de Educação",
        "objeto": "Aquisição de materiais escolares",
        "justificativa": "Atender os estudantes da rede municipal no ano letivo.",
        "quantitativo": 500,
        "unidade_medida": "kits",
        "valor_estimado": "12500.50",
        "fonte_estimativa": "Pesquisa de mercado",
        "prazo_vigencia_meses": 12,
        "data_pretendida": "2027-02-01",
        "responsavel_nome": "Responsável de teste",
        "responsavel_cargo": "Servidor",
        "responsavel_matricula": "123",
        "autoridade_nome": "Autoridade de teste",
        "autoridade_cargo": "Secretária Municipal de Educação",
        "codigo_pncp": "",
        "fundamento": "Lei Federal nº 14.133/2021",
    }


class TestDFD(unittest.TestCase):
    def test_lista_os_seis_tipos_oficiais(self) -> None:
        self.assertEqual(len(listar_tipos_dfd()), 6)

    def test_gera_pregao_com_formatacao_brasileira(self) -> None:
        resultado = gerar_dfd("pregao", dados_validos())
        self.assertIn("PREGÃO", resultado["titulo"])
        self.assertIn("R$ 12.500,50", resultado["conteudo"])
        self.assertIn("01/02/2027", resultado["conteudo"])
        self.assertNotIn("CONTRATADA:", resultado["conteudo"])

    def test_exige_contratada_na_dispensa(self) -> None:
        with self.assertRaisesRegex(ValueError, "Nome da contratada"):
            gerar_dfd("dispensa", dados_validos())

    def test_gera_dispensa_com_contratada(self) -> None:
        dados = dados_validos()
        dados["contratada_nome"] = "Empresa de Teste Ltda."
        dados["contratada_documento"] = "00.000.000/0001-00"
        resultado = gerar_dfd("dispensa", dados)
        self.assertIn("Empresa de Teste Ltda.", resultado["conteudo"])

    def test_rejeita_valores_nao_positivos(self) -> None:
        dados = dados_validos()
        dados["valor_estimado"] = 0
        with self.assertRaisesRegex(ValueError, "maior que zero"):
            gerar_dfd("pregao", dados)

    def test_rejeita_tipo_desconhecido(self) -> None:
        with self.assertRaisesRegex(ValueError, "inválido"):
            gerar_dfd("outro", dados_validos())


if __name__ == "__main__":
    unittest.main()
