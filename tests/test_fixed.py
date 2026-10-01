import importlib.machinery
import importlib.util
import json
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "bin" / "asimov-fixed"
LOADER = importlib.machinery.SourceFileLoader("asimov_fixed", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC
asimov = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(asimov)


class DiscoveryTests(unittest.TestCase):
    def test_discovers_outputs_and_collapses_worktrees(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            root = home / "code"
            cargo = root / "app"
            (cargo / "target").mkdir(parents=True)
            (cargo / "Cargo.toml").touch()
            web = root / "web"
            (web / "node_modules").mkdir(parents=True)
            (web / "package.json").touch()
            worktrees = root / "app__worktrees"
            nested_target = worktrees / "feature" / "target"
            nested_target.mkdir(parents=True)
            (nested_target.parent / "Cargo.toml").touch()
            explicit = home / "node_modules"
            explicit.mkdir()

            paths, errors = asimov.discover(
                {
                    "home": str(home),
                    "roots": ["~/code"],
                    "explicit_paths": ["~/node_modules"],
                    "exclude_worktree_roots": True,
                }
            )

            self.assertEqual(errors, [])
            self.assertEqual(
                set(paths),
                {
                    explicit.resolve(),
                    (cargo / "target").resolve(),
                    (web / "node_modules").resolve(),
                    worktrees.resolve(),
                },
            )

    def test_missing_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths, errors = asimov.discover(
                {"home": temporary, "roots": ["~/missing"], "explicit_paths": []}
            )
            self.assertEqual(paths, [])
            self.assertEqual(len(errors), 1)


class ExclusionTests(unittest.TestCase):
    def test_reads_fixed_exclusions_from_preferences(self):
        payload = plistlib.dumps({"SkipPaths": ["/tmp/a", "/tmp/b"]})
        result = mock.Mock(stdout=payload)
        with mock.patch.object(asimov, "run", return_value=result):
            self.assertEqual(
                asimov.read_fixed_exclusions(),
                {asimov.canonical(Path("/tmp/a")), asimov.canonical(Path("/tmp/b"))},
            )

    def test_manifest_verification_reports_missing_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            manifest = destination / "2026-10-01.backup" / ".exclusions.plist"
            manifest.parent.mkdir()
            manifest.write_bytes(
                plistlib.dumps({"userExclusionPaths": ["/tmp/a"]})
            )
            result = asimov.verify_manifest(
                {"backup_destination": str(destination)},
                {asimov.canonical(Path("/tmp/a")), asimov.canonical(Path("/tmp/b"))},
                0,
            )
            self.assertEqual(result["state"], "failed")
            self.assertEqual(result["missing"], [str(asimov.canonical(Path("/tmp/b")))])

    def test_resolved_output_root_is_allowed(self):
        config = {
            "home": "/Users/test",
            "roots": ["~/code"],
            "resolved_output_roots": ["~/Library/Caches/mbx/targets"],
        }
        asimov.validate_managed_path(
            Path("/Users/test/Library/Caches/mbx/targets/project"), config
        )
        with self.assertRaises(asimov.AsimovError):
            asimov.validate_managed_path(Path("/Users/test/elsewhere/target"), config)

    def test_repeated_notification_is_suppressed(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "notification.json"
            with mock.patch.object(asimov, "notification_state_path", return_value=state):
                self.assertTrue(asimov.should_notify("failure"))
                self.assertFalse(asimov.should_notify("failure"))
                self.assertTrue(asimov.should_notify("different failure"))

    def test_configuration_is_json(self):
        config = json.loads(
            (Path(__file__).parents[1] / "config" / "raine.json").read_text()
        )
        self.assertTrue(config["exclude_worktree_roots"])


if __name__ == "__main__":
    unittest.main()
