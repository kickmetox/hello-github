import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crossos.migrator.semantic import translate_document

ROOT = Path(__file__).resolve().parents[1]


class SemanticTests(unittest.TestCase):
    def test_gitconfig_to_reg(self):
        text = (ROOT / "examples" / "gitconfig.sample").read_text(encoding="utf-8")
        result = translate_document(text, target_format="reg", target_os="windows", user="andreas")
        self.assertEqual(result["profile"], "gitconfig")
        self.assertFalse(result["executed"])
        self.assertIn(r"HKEY_CURRENT_USER\Software\Git\core", result["output"])
        self.assertIn(r"C:\\Users\\andreas\\AppData\\Local\\bin\\nvim", result["output"])
        self.assertIn(r"C:\\Users\\andreas\\AppData\\Roaming\\git\\ignore", result["output"])
        self.assertIn('"autocrlf"="true"', result["output"])
        kinds = {change["kind"] for change in result["changes"]}
        self.assertIn("path", kinds)
        self.assertIn("semantic", kinds)

    def test_reg_back_to_linux_ini(self):
        text = (ROOT / "examples" / "app.reg").read_text(encoding="utf-8")
        result = translate_document(text, target_format="ini", target_os="linux", source_format="reg")
        self.assertIn("autocrlf = input", result["output"])
        self.assertIn("/home/andreas/.local/bin/nvim", result["output"])

    def test_vscode_json_keys_and_eol(self):
        text = (ROOT / "examples" / "vscode-settings.json").read_text(encoding="utf-8")
        result = translate_document(text, target_format="json", target_os="windows", source_format="json", user="andreas")
        data = json.loads(result["output"])
        self.assertEqual(result["profile"], "vscode")
        self.assertIn("terminal.integrated.defaultProfile.windows", data)
        self.assertNotIn("terminal.integrated.defaultProfile.linux", data)
        self.assertEqual(data["files.eol"], "\r\n")
        self.assertEqual(data["python.defaultInterpreterPath"], r"C:\Users\andreas\AppData\Local\bin\python3")
        self.assertEqual(data["terminal.integrated.defaultProfile.windows"], "bash")

    def test_bashrc_paths(self):
        text = (ROOT / "examples" / "bashrc.sample").read_text(encoding="utf-8")
        result = translate_document(text, target_format="bash", target_os="windows", source_format="bash", user="andreas")
        self.assertIn(r"C:\Users\andreas\AppData\Local\bin\nvim", result["output"])
        self.assertIn(r"C:\Users\andreas\Documents", result["output"])
        self.assertIn("export ", result["output"])
        self.assertFalse(result["executed"])

    def test_xml_path(self):
        text = (ROOT / "examples" / "appdata.xml").read_text(encoding="utf-8")
        result = translate_document(text, target_format="xml", target_os="windows", source_format="xml")
        self.assertIn(r"C:\Users\andreas\AppData\Roaming\nvim\init.vim", result["output"])


if __name__ == "__main__":
    unittest.main()
