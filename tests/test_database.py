import tempfile
import unittest
from pathlib import Path

from database import Repositorio


class TestRepositorio(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Repositorio(Path(self.temp.name) / "teste.db")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_cria_e_lista_contratacao(self) -> None:
        criada = self.repo.criar_contratacao(
            "Materiais escolares", "Secretaria de Educação", "Aquisição de kits"
        )
        self.assertEqual(criada["id"], 1)
        lista = self.repo.listar_contratacoes()
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["total_documentos"], 0)

    def test_salva_versoes_sem_sobrescrever(self) -> None:
        contratacao = self.repo.criar_contratacao(
            "Transporte escolar", "Secretaria de Educação"
        )
        primeira = self.repo.salvar_documento(
            contratacao["id"], "dfd", "pregao", {"objeto": "Versão inicial"}
        )
        segunda = self.repo.salvar_documento(
            contratacao["id"], "dfd", "pregao", {"objeto": "Versão revisada"}
        )
        self.assertEqual(primeira["versao"], 1)
        self.assertEqual(segunda["versao"], 2)
        self.assertEqual(
            self.repo.obter_documento(primeira["id"])["dados"]["objeto"],
            "Versão inicial",
        )
        self.assertEqual(len(self.repo.listar_documentos(contratacao["id"])), 2)

    def test_separa_versao_por_tipo_e_subtipo(self) -> None:
        contratacao = self.repo.criar_contratacao(
            "Contratação de teste", "Secretaria de Educação"
        )
        dfd = self.repo.salvar_documento(
            contratacao["id"], "dfd", "pregao", {"campo": "a"}
        )
        etp = self.repo.salvar_documento(
            contratacao["id"], "etp", "compras_servicos", {"campo": "b"}
        )
        self.assertEqual(dfd["versao"], 1)
        self.assertEqual(etp["versao"], 1)

    def test_rejeita_contratacao_inexistente(self) -> None:
        with self.assertRaisesRegex(ValueError, "não encontrada"):
            self.repo.salvar_documento(999, "dfd", "pregao", {})


if __name__ == "__main__":
    unittest.main()
