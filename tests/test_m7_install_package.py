import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from redaction_assistant.install_package import build_install_package


class M7InstallPackageTests(unittest.TestCase):
    def test_build_install_package_creates_testable_windows_package(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.7.0-m7")

            package_dir = result["package_dir"]
            archive = result["archive"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            archive_names = set(zipfile.ZipFile(archive).namelist())

            self.assertTrue(package_dir.exists())
            self.assertTrue(archive.exists())
            self.assertEqual(archive.name, "document_redaction_assistant_install_0.7.0-m7.zip")
            self.assertEqual(manifest["schema_version"], "document_redaction_install_manifest.v1")
            self.assertEqual(manifest["version"], "0.7.0-m7")
            self.assertEqual(manifest["entrypoint"], "START_HERE.md")
            self.assertIn("run_sample_self_test.bat", manifest["smoke_test"])
            self.assertTrue((package_dir / "START_HERE.md").exists())
            self.assertTrue((package_dir / "app" / "run_cli.bat").exists())
            self.assertTrue((package_dir / "app" / "register_community.bat").exists())
            self.assertTrue((package_dir / "app" / "start_local_service.bat").exists())
            self.assertTrue((package_dir / "app" / "run_sample_self_test.bat").exists())
            self.assertTrue((package_dir / "app" / "src" / "redaction_assistant" / "cli.py").exists())
            self.assertTrue((package_dir / "app" / "desktop_shell" / "index.html").exists())
            self.assertTrue((package_dir / "sample_data" / "project_alpha" / "input.txt").exists())
            self.assertFalse((package_dir / "app" / "local_mapping.private.json").exists())
            self.assertIn(f"{package_dir.name}/START_HERE.md", archive_names)
            self.assertIn(f"{package_dir.name}/app/run_cli.bat", archive_names)
            self.assertIn(f"{package_dir.name}/app/register_community.bat", archive_names)
            self.assertIn(f"{package_dir.name}/app/desktop_shell/index.html", archive_names)
            for name in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"):
                self.assertEqual((ROOT / name).read_bytes(), (package_dir / name).read_bytes())
                self.assertIn(f"{package_dir.name}/{name}", archive_names)

            run_cli = (package_dir / "app" / "run_cli.bat").read_text(encoding="utf-8")
            register = (package_dir / "app" / "register_community.bat").read_text(encoding="utf-8")
            self_test = (package_dir / "app" / "run_sample_self_test.bat").read_text(encoding="utf-8")
            start_here = (package_dir / "START_HERE.md").read_text(encoding="utf-8")
            self.assertNotIn("DRA_REGISTRATION_DIR", run_cli)
            self.assertIn("PYTHONPATH", run_cli)
            self.assertNotIn("registration-request", register)
            self.assertIn("不再需要注册", register)
            self.assertIn("不执行任何操作", register)
            self.assertNotIn("--registration-dir", self_test)
            self.assertIn("--mapping-passphrase", self_test)
            self.assertNotIn("50 个文件", start_here)
            self.assertIn("使用必读", start_here)
            self.assertNotIn("registration", manifest["commands"])
            self.assertEqual(manifest["commands"]["local_service"], "app\\start_local_service.bat")
            self.assertNotIn("registration_trial_gate", manifest["capabilities"])

    def test_build_install_package_bundles_core_wheelhouse_when_provided(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wheelhouse = root / "wheels"
            wheelhouse.mkdir()
            for name in _CORE_WHEEL_NAMES:
                (wheelhouse / name).write_bytes(b"wheel")

            result = build_install_package(root / "out", version="0.27.0", wheelhouse=wheelhouse)

            package_dir = result["package_dir"]
            app = package_dir / "app"
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))
            bundled = sorted(path.name for path in (app / "wheels").glob("*.whl"))
            run_cli = (app / "run_cli.bat").read_text(encoding="utf-8")
            installer = (app / "install_core_deps.bat").read_text(encoding="utf-8")

            self.assertEqual(sorted(_CORE_WHEEL_NAMES), bundled)
            self.assertEqual(sorted(_CORE_WHEEL_NAMES), sorted(manifest["core_dependencies"]["bundled_wheels"]))
            self.assertIn("bundled_core_dependency_wheels", manifest["capabilities"])
            self.assertEqual("app\\requirements.txt", manifest["core_dependencies"]["requirements"])
            self.assertEqual("app\\install_core_deps.bat", manifest["commands"]["install_core_deps"])
            self.assertTrue((app / "requirements.txt").exists())
            self.assertIn("--no-index", installer)
            self.assertIn("--find-links", installer)
            self.assertIn("core_dependencies.py", run_cli)
            self.assertIn("install_core_deps.bat", run_cli)

    def test_build_install_package_without_wheelhouse_records_no_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            result = build_install_package(Path(td), version="0.27.0")
            package_dir = result["package_dir"]
            manifest = json.loads((package_dir / "install_manifest.json").read_text(encoding="utf-8"))

            self.assertFalse((package_dir / "app" / "wheels").exists())
            self.assertEqual([], manifest["core_dependencies"]["bundled_wheels"])
            self.assertIsNone(manifest["core_dependencies"]["wheelhouse_dir"])
            self.assertNotIn("bundled_core_dependency_wheels", manifest["capabilities"])
            self.assertTrue((package_dir / "app" / "install_core_deps.bat").exists())

    def test_core_wheelhouse_must_be_complete_and_version_compatible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            incomplete = root / "incomplete"
            incomplete.mkdir()
            for name in _CORE_WHEEL_NAMES:
                if name.startswith("cffi-"):
                    continue
                (incomplete / name).write_bytes(b"wheel")
            with self.assertRaises(ValueError):
                build_install_package(root / "out1", version="0.27.0", wheelhouse=incomplete)

            incompatible = root / "incompatible"
            incompatible.mkdir()
            for name in _CORE_WHEEL_NAMES:
                if name.startswith("cryptography-"):
                    (incompatible / "cryptography-50.0.2-cp39-abi3-win_amd64.whl").write_bytes(b"wheel")
                else:
                    (incompatible / name).write_bytes(b"wheel")
            with self.assertRaises(ValueError):
                build_install_package(root / "out2", version="0.27.0", wheelhouse=incompatible)


_CORE_WHEEL_NAMES = (
    "cryptography-42.0.8-cp39-abi3-win_amd64.whl",
    "cffi-1.17.1-cp311-cp311-win_amd64.whl",
    "pycparser-2.22-py3-none-any.whl",
    "pypdf-6.21.1-py3-none-any.whl",
    "defusedxml-0.7.1-py3-none-any.whl",
)


if __name__ == "__main__":
    unittest.main()
