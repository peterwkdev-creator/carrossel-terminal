"""O README: os exemplos em Python rodam como estão (nenhum deles abre o navegador)."""
import contextlib
import io
import os
import pathlib
import re
import sys
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
README = RAIZ / "README.md"


class TestExemplosDoReadme(unittest.TestCase):

    def test_blocos_python_rodam(self):
        blocos = re.findall(r"```python\n(.*?)```", README.read_text(encoding="utf-8"), re.S)
        self.assertGreaterEqual(len(blocos), 1)
        sys.path.insert(0, str(RAIZ))
        antes = os.getcwd()
        os.chdir(RAIZ)  # os exemplos usam caminhos relativos à raiz do repositório
        try:
            for i, bloco in enumerate(blocos, 1):
                # o print dos exemplos não sai no meio dos testes
                with self.subTest(bloco=i), contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(bloco, f"README, bloco {i}", "exec"), {})
        finally:
            os.chdir(antes)

    def test_comandos_citados_existem(self):
        # todo "python <script>.py" do README aponta um arquivo do repositório
        scripts = set(re.findall(r"python (\w+\.py)", README.read_text(encoding="utf-8")))
        self.assertTrue(scripts)
        for s in scripts:
            with self.subTest(script=s):
                self.assertTrue((RAIZ / s).is_file())


if __name__ == "__main__":
    unittest.main()
