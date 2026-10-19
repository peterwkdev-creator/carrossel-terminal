"""gerar.py: o texto.md do exemplo vira um HTML por slide (sem navegador)."""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import gerar  # noqa: E402


class TestGerar(unittest.TestCase):

    def test_exemplo_vira_html(self):
        # numa cópia, para o teste não deixar html/ no exemplo
        with tempfile.TemporaryDirectory() as tmp:
            post = pathlib.Path(tmp) / "post-exemplo"
            shutil.copytree(RAIZ / "exemplos" / "post-exemplo", post)
            r = subprocess.run([sys.executable, str(RAIZ / "gerar.py"), str(post), "--sem-png"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("5 slides em HTML", r.stdout)
            arqs = sorted((post / "html").glob("slide-*.html"))
            self.assertEqual([a.name for a in arqs], [f"slide-{i:02d}.html" for i in range(1, 6)])
            capa = arqs[0].read_text(encoding="utf-8")
            self.assertIn("<h1>Revise o commit antes do push</h1>", capa)
            self.assertIn('<body class="tipo-capa">', capa)
            self.assertIn("<b>01</b>/05", capa)
            self.assertIn("deslize →", capa)
            # a nota de conferência (linha com ">") não vai para a imagem
            self.assertNotIn("Nota de conferência", arqs[1].read_text(encoding="utf-8"))
            self.assertIn("<th>em vez de</th>", arqs[2].read_text(encoding="utf-8"))

    def test_marcacao_em_linha(self):
        self.assertEqual(gerar.em_linha("**a** `b` !!c!! <d>"),
                         '<b class="dest">a</b> <code>b</code> <b class="alerta">c</b> &lt;d&gt;')

    def test_formatos(self):
        self.assertEqual(gerar.dimensoes({}), (1080, 1350))
        self.assertEqual(gerar.dimensoes({"formato": "3:4"}), (1080, 1440))
        with self.assertRaises(SystemExit):
            gerar.dimensoes({"formato": "1:1"})

    def test_versao(self):
        r = subprocess.run([sys.executable, str(RAIZ / "gerar.py"), "--versao"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.stdout.strip(), gerar.__version__)


if __name__ == "__main__":
    unittest.main()
