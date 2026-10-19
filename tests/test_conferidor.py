"""conferir.py nas duas provas: o plantado reprova citando cada defeito; o limpo passa.

Precisa do Chrome, Chromium ou Edge (sem ele, os testes são pulados) e de rede:
o link morto plantado tem de dar 404.
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import gerar  # noqa: E402
import provas  # noqa: E402

PLANTADO = RAIZ / "provas" / "plantado"
LIMPO = RAIZ / "provas" / "limpo"


def rodar(*args):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


@unittest.skipUnless(gerar.achar_chrome(), "sem Chrome/Chromium: o conferidor não roda")
class TestConferidor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        provas.capturas_de_prova(PLANTADO, LIMPO)
        for p in (PLANTADO, LIMPO):
            cod, saida = rodar(RAIZ / "gerar.py", p, "--sem-png")
            assert cod == 0, saida

    def test_plantado_reprova_com_cada_defeito(self):
        cod, saida = rodar(RAIZ / "conferir.py", PLANTADO)
        self.assertEqual(cod, 1, saida)
        for chave, nome in provas.ESPERADOS.items():
            with self.subTest(defeito=nome):
                self.assertIn(chave, saida)

    def test_limpo_passa_sem_defeito(self):
        cod, saida = rodar(RAIZ / "conferir.py", LIMPO)
        self.assertEqual(cod, 0, saida)
        self.assertNotIn("DEFEITO", saida)

    def test_exemplo_passa_para_publicar(self):
        with tempfile.TemporaryDirectory() as tmp:
            post = pathlib.Path(tmp) / "post-exemplo"
            shutil.copytree(RAIZ / "exemplos" / "post-exemplo", post)
            rodar(RAIZ / "gerar.py", post, "--sem-png")
            cod, saida = rodar(RAIZ / "conferir.py", post, "--publicar")
            self.assertEqual(cod, 0, saida)
            self.assertIn("APROVADO", saida)


if __name__ == "__main__":
    unittest.main()
