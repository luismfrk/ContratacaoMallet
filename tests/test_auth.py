import tempfile
import unittest
from pathlib import Path

from auth import (
    ServicoAutenticacao,
    hash_token,
    perfil_autocadastro,
    validar_senha_nova,
)
from database import Repositorio


class TestAutenticacao(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Repositorio(Path(self.temp.name) / "auth.db")
        self.auth = ServicoAutenticacao(self.repo)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_senha_fica_com_hash_argon2(self) -> None:
        usuario = self.auth.criar_usuario(
            "Administrador de Teste", "admin", "SenhaForte123", "admin"
        )
        armazenado = self.repo.obter_usuario_por_login("admin")
        self.assertEqual(usuario["login"], "admin")
        self.assertTrue(armazenado["senha_hash"].startswith("$argon2"))
        self.assertNotIn("senha_hash", usuario)

    def test_autentica_e_cria_sessao(self) -> None:
        criado = self.auth.criar_usuario(
            "Usuário de Teste", "usuario", "OutraSenha456", "editor"
        )
        autenticado = self.auth.autenticar("usuario", "OutraSenha456")
        self.assertEqual(autenticado["id"], criado["id"])
        token = self.auth.iniciar_sessao(criado["id"])
        self.assertGreater(len(token), 30)
        self.assertEqual(self.auth.usuario_da_sessao(token)["id"], criado["id"])
        self.assertNotEqual(token, hash_token(token))

    def test_rejeita_senha_incorreta(self) -> None:
        self.auth.criar_usuario(
            "Usuário de Teste", "usuario", "OutraSenha456", "editor"
        )
        self.assertIsNone(self.auth.autenticar("usuario", "senha-errada"))

    def test_exige_senha_minimamente_forte(self) -> None:
        with self.assertRaises(ValueError):
            validar_senha_nova("curta")
        with self.assertRaises(ValueError):
            validar_senha_nova("somenteletras")

    def test_registra_autor_da_versao(self) -> None:
        usuario = self.auth.criar_usuario(
            "Responsável de Teste", "responsavel", "SenhaSegura789", "editor"
        )
        contratacao = self.repo.criar_contratacao(
            "Processo de teste",
            "Secretaria de Educação",
            usuario_id=usuario["id"],
        )
        documento = self.repo.salvar_documento(
            contratacao["id"],
            "dfd",
            "pregao",
            {"objeto": "Teste"},
            usuario_id=usuario["id"],
        )
        self.assertEqual(documento["criado_por"], "Responsável de Teste")
        historico = self.repo.listar_documentos(contratacao["id"])
        self.assertEqual(historico[0]["criado_por"], "Responsável de Teste")

    def test_apenas_primeiro_autocadastro_e_admin(self) -> None:
        self.assertEqual(perfil_autocadastro(0), "admin")
        self.assertEqual(perfil_autocadastro(1), "editor")
        self.assertEqual(perfil_autocadastro(10), "editor")


if __name__ == "__main__":
    unittest.main()
