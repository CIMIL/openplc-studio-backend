import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from plc_platform_backend.commons.configuration.configuration import get_configuration
from plc_platform_backend.modules.modules_models import ModuleType
from plc_platform_backend.modules.modules_repository import ModulesRepository
from plc_platform_backend.plugins.plugins_models import PluginStatus
from plc_platform_backend.plugins.plugins_service import PluginsService


VALID_PLUGIN = '''"""
- name: Demo
  settings:
    - name: strength
      type: float
      default: 0.5
      values: null
"""

class DemoSettings:
    pass

class Demo:
    pass
'''


class PluginsServiceTests(TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.plugins_directory = Path(self.temporary_directory.name)
        self.environment = patch.dict(
            os.environ,
            {
                "MONGO_INITDB_ROOT_USERNAME": "test",
                "MONGO_INITDB_ROOT_PASSWORD": "test",
                "PLC_ROOT_FOLDER": str(self.plugins_directory / "artifacts"),
                "PLUGINS_DIRECTORY": str(self.plugins_directory),
                "REDIS_URL": "redis://localhost:6379/0",
            },
        )
        self.environment.start()
        get_configuration.cache_clear()

    def tearDown(self) -> None:
        get_configuration.cache_clear()
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_discovers_available_plugin(self) -> None:
        (self.plugins_directory / "DemoAlgorithm.py").write_text(VALID_PLUGIN)

        inventory = PluginsService().scan()

        self.assertEqual(len(inventory.items), 1)
        plugin = inventory.items[0]
        self.assertEqual(plugin.filename, "DemoAlgorithm.py")
        self.assertEqual(plugin.status, PluginStatus.AVAILABLE)
        self.assertEqual(plugin.module_type, ModuleType.PLCAlgorithm)
        self.assertIsNotNone(plugin.spec)
        assert plugin.spec is not None
        self.assertEqual(plugin.spec.name, "Demo")
        self.assertTrue(plugin.spec.is_plugin)
        self.assertEqual(plugin.spec.settings[0].name, "strength")
        self.assertIsNone(plugin.error)

    def test_reports_invalid_plugins(self) -> None:
        cases = [
            ("BrokenAlgorithm.py", "def broken(:\n", "Python syntax error"),
            ("BrokenAlgorithm.py", "class Broken: pass\n", "Missing module docstring"),
            ("BrokenAlgorithm.py", '"""not: [valid"""', "while parsing"),
            (
                "BrokenAlgorithm.py",
                '"""\n- settings: []\n"""\nclass BrokenSettings: pass\nclass Broken: pass\n',
                "Invalid manifest",
            ),
            ("WrongAlgorithm.py", VALID_PLUGIN, "Expected filename 'DemoAlgorithm.py'"),
            (
                "DemoAlgorithm.py",
                '"""\n- name: Demo\n  settings: []\n"""\nclass Demo: pass\n',
                "Missing required class(es): DemoSettings",
            ),
        ]

        for filename, content, message in cases:
            with self.subTest(filename=filename, message=message):
                for path in self.plugins_directory.glob("*.py"):
                    path.unlink()
                (self.plugins_directory / filename).write_text(content)

                plugin = PluginsService().scan().items[0]

                self.assertEqual(plugin.status, PluginStatus.INVALID)
                self.assertIsNone(plugin.spec)
                self.assertIn(message, plugin.error or "")

    def test_scan_is_sorted_and_reflects_filesystem_changes(self) -> None:
        (self.plugins_directory / "ZuluAlgorithm.py").write_text(
            VALID_PLUGIN.replace("Demo", "Zulu")
        )
        (self.plugins_directory / "AlphaAlgorithm.py").write_text(
            VALID_PLUGIN.replace("Demo", "Alpha")
        )
        service = PluginsService()

        self.assertEqual(
            [item.filename for item in service.scan().items],
            ["AlphaAlgorithm.py", "ZuluAlgorithm.py"],
        )

        (self.plugins_directory / "AlphaAlgorithm.py").unlink()
        self.assertEqual(
            [item.filename for item in service.scan().items],
            ["ZuluAlgorithm.py"],
        )

    def test_file_read_errors_do_not_expose_absolute_paths(self) -> None:
        plugin_path = self.plugins_directory / "DemoAlgorithm.py"
        plugin_path.write_text(VALID_PLUGIN)

        with patch.object(Path, "read_text", side_effect=PermissionError(13, "Permission denied", str(plugin_path))):
            plugin = PluginsService().scan().items[0]

        self.assertEqual(plugin.status, PluginStatus.INVALID)
        self.assertEqual(plugin.error, "Could not read plugin file: Permission denied")
        self.assertNotIn(str(self.plugins_directory), plugin.error or "")

    def test_invalid_plugin_does_not_hide_available_plugins(self) -> None:
        (self.plugins_directory / "DemoAlgorithm.py").write_text(VALID_PLUGIN)
        (self.plugins_directory / "BrokenAlgorithm.py").write_text("def broken(:")

        inventory = PluginsService().scan()

        self.assertEqual(
            {item.status for item in inventory.items},
            {PluginStatus.AVAILABLE, PluginStatus.INVALID},
        )

    def test_modules_repository_only_returns_available_plugins(self) -> None:
        (self.plugins_directory / "DemoAlgorithm.py").write_text(VALID_PLUGIN)
        (self.plugins_directory / "BrokenAlgorithm.py").write_text("def broken(:")

        modules = ModulesRepository().get_all_modules_by_type(ModuleType.PLCAlgorithm)

        self.assertIn("Demo", [module.name for module in modules])
        self.assertNotIn("Broken", [module.name for module in modules])
        self.assertTrue(next(module for module in modules if module.name == "Demo").is_plugin)
        self.assertFalse(next(module for module in modules if module.name == "AdvancedPLC").is_plugin)
