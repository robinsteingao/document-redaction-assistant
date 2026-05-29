import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.commercial_package import build_commercial_install_package
from redaction_assistant.install_package import build_install_package


class M18RealRuntimePackageTests(unittest.TestCase):
    def test_run_cli_prefers_embedded_python_when_present(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.18.0-m18")
            run_cli = (result["package_dir"] / "app" / "run_cli.bat").read_text(encoding="utf-8")

            self.assertIn('set "EMBEDDED_PY=%APP_DIR%runtime\\python\\python.exe"', run_cli)
            self.assertIn('offline_ocr_installed.marker.json', run_cli)
            self.assertIn('offline_ocr_env.bat', run_cli)
            self.assertLess(run_cli.index("EMBEDDED_PY"), run_cli.index("where python"))
            self.assertIn('"%EMBEDDED_PY%" -m redaction_assistant.cli %*', run_cli)

    def test_commercial_package_marks_runtime_commands_as_embedded_first(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            python_runtime = root / "python_runtime"
            ocr_wheelhouse = root / "ocr_wheelhouse"
            office_runtime = root / "office_runtime"
            python_runtime.mkdir()
            ocr_wheelhouse.mkdir()
            office_runtime.mkdir()
            (python_runtime / "python.exe").write_bytes(b"python-runtime")
            (ocr_wheelhouse / "paddlepaddle-2.6.2-cp311-cp311-win_amd64.whl").write_bytes(b"wheel")
            (ocr_wheelhouse / "paddleocr-2.8.1.tar.gz").write_bytes(b"source")
            (office_runtime / "soffice.exe").write_bytes(b"office-runtime")

            result = build_commercial_install_package(
                root / "release",
                version="0.18.0-m18",
                python_runtime_dir=python_runtime,
                ocr_wheelhouse_dir=ocr_wheelhouse,
                office_runtime_dir=office_runtime,
            )
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            run_cli = (package_dir / "app" / "run_cli.bat").read_text(encoding="utf-8")
            start_offline = (package_dir / "app" / "start_offline_app.bat").read_text(encoding="utf-8")
            embedded_launcher = (package_dir / "app" / "runtime" / "run_with_embedded_python.bat").read_text(encoding="utf-8")

            self.assertEqual(manifest["runtime_mode"], "embedded_python_first")
            self.assertIn("embedded_runtime_preferred", manifest["capabilities"])
            self.assertIn('"%EMBEDDED_PY%" -m redaction_assistant.cli %*', run_cli)
            self.assertIn("call run_cli.bat serve-local", start_offline)
            self.assertIn("offline_ocr_env.bat", embedded_launcher)

    def test_python_runtime_staging_keeps_pip_without_unrelated_site_packages(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            python_runtime = root / "python_runtime"
            ocr_wheelhouse = root / "ocr_wheelhouse"
            office_runtime = root / "office_runtime"
            (python_runtime / "Lib" / "site-packages" / "pip").mkdir(parents=True)
            (python_runtime / "Lib" / "site-packages" / "_distutils_hack").mkdir(parents=True)
            (python_runtime / "Lib" / "site-packages" / "numpy").mkdir(parents=True)
            ocr_wheelhouse.mkdir()
            office_runtime.mkdir()
            (python_runtime / "python.exe").write_bytes(b"python-runtime")
            (python_runtime / "Lib" / "os.py").write_text("# stdlib", encoding="utf-8")
            (python_runtime / "Lib" / "site-packages" / "pip" / "__init__.py").write_text("", encoding="utf-8")
            (python_runtime / "Lib" / "site-packages" / "_distutils_hack" / "__init__.py").write_text("", encoding="utf-8")
            (python_runtime / "Lib" / "site-packages" / "numpy" / "__init__.py").write_text("", encoding="utf-8")
            (ocr_wheelhouse / "paddlepaddle-2.6.2-cp311-cp311-win_amd64.whl").write_bytes(b"wheel")
            (ocr_wheelhouse / "paddleocr-2.8.1.tar.gz").write_bytes(b"source")
            (office_runtime / "soffice.exe").write_bytes(b"office-runtime")

            result = build_commercial_install_package(
                root / "release",
                version="0.18.0-m18",
                python_runtime_dir=python_runtime,
                ocr_wheelhouse_dir=ocr_wheelhouse,
                office_runtime_dir=office_runtime,
            )
            staged_site = result["package_dir"] / "app" / "runtime" / "python" / "Lib" / "site-packages"

            self.assertTrue((staged_site / "pip").exists())
            self.assertTrue((staged_site / "_distutils_hack").exists())
            self.assertFalse((staged_site / "numpy").exists())


if __name__ == "__main__":
    unittest.main()
