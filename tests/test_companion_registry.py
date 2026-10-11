"""Regression checks for dependency provenance and inactive public defaults."""
import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/second-founder"
SPEC = importlib.util.spec_from_file_location("second_founder_validate", ROOT / "scripts/validate.py")
VALIDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATE)


class CompanionRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((SKILL / "assets/companion-registry.json").read_text(encoding="utf-8"))

    def changed(self, field, value):
        candidate = copy.deepcopy(self.registry)
        candidate["providers"][0][field] = value
        return candidate

    def assert_invalid(self, candidate, message):
        errors = VALIDATE.validate_companion_registry(candidate)
        self.assertTrue(any(message in error for error in errors), errors)

    def test_bundled_registry_has_reviewed_provenance(self):
        self.assertEqual(VALIDATE.validate_companion_registry(self.registry), [])

    def test_source_cannot_be_replaced_by_other_repository_or_host(self):
        for source in ("https://example.com/owner/repo", "https://github.com/other/repository",
                       "http://github.com/owner/repo", "https://github.com/owner/repo?ref=main"):
            with self.subTest(source=source):
                self.assert_invalid(self.changed("source_url", source), "source_url")
        for repository in ("https://github.com/owner/repo", "owner/repo/extra", "owner/repo;run", "../repo"):
            with self.subTest(repository=repository):
                self.assert_invalid(self.changed("repository", repository), "repository")

    def test_refs_cannot_float_or_use_abbreviated_commits(self):
        for ref in ("main", "v1.0.0", "a" * 7, "g" * 40, "a" * 41, None, 123):
            with self.subTest(ref=ref):
                self.assert_invalid(self.changed("ref", ref), "pinned")

    def test_paths_reject_traversal_absolute_paths_and_shell_fragments(self):
        for unsafe in ("../outside", "skills/../outside", "skills//name", "/tmp/skill",
                       "C:/skills/name", "C:\\skills\\name", "\\\\server\\share", "~/skills",
                       "skills/$(command)", "skills/one;command", "skills/one|command",
                       "skills/`command`", "--help", "skills/con", "skills/name."):
            with self.subTest(path=unsafe):
                candidate = copy.deepcopy(self.registry)
                candidate["providers"][0]["skills"][0]["path"] = unsafe
                self.assert_invalid(candidate, "safe relative folder")
                self.assert_invalid(self.changed("license_path", unsafe), "safe relative path")
        for safe in (".", "skills/name", ".agents/skills/name"):
            candidate = copy.deepcopy(self.registry)
            candidate["providers"][0]["skills"][0]["path"] = safe
            self.assertEqual(VALIDATE.validate_companion_registry(candidate), [])

    def test_provider_and_skill_duplicates_are_rejected(self):
        candidate = copy.deepcopy(self.registry)
        candidate["providers"].append(copy.deepcopy(candidate["providers"][0]))
        self.assert_invalid(candidate, "duplicate id")
        candidate = copy.deepcopy(self.registry)
        candidate["providers"][0]["skills"].append(copy.deepcopy(candidate["providers"][0]["skills"][0]))
        self.assert_invalid(candidate, "duplicate name")

    def test_review_date_must_be_real_and_unambiguous(self):
        for reviewed in ("2026-02-30", "2026-2-3", "11/10/2026", "yesterday", "2026-10-11T00:00:00Z", None):
            with self.subTest(reviewed=reviewed):
                candidate = copy.deepcopy(self.registry)
                candidate["reviewed_on"] = reviewed
                self.assert_invalid(candidate, "reviewed_on")

    def test_unknown_license_and_installation_strategy_are_rejected(self):
        self.assert_invalid(self.changed("license", "unknown"), "license")
        self.assert_invalid(self.changed("installation_unit", "execute_remote_script"), "installation_unit")
        candidate = copy.deepcopy(self.registry)
        candidate["install_policy"] = "install_everything"
        self.assert_invalid(candidate, "install_policy")

    def test_missing_required_fields_and_wrong_types_return_errors(self):
        for field in self.registry["providers"][0]:
            if field not in {"id", "repository", "source_url", "ref", "license", "license_path",
                             "installation_unit", "roles", "skills", "requirements", "constraints", "fallback"}:
                continue
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.registry)
                del candidate["providers"][0][field]
                self.assertTrue(VALIDATE.validate_companion_registry(candidate))
        for data in (None, [], {"schema_version": True}, {"providers": [None]}):
            self.assertTrue(VALIDATE.validate_companion_registry(data))
        for field, value in (("id", []), ("roles", []), ("requirements", "python"),
                             ("constraints", [""]), ("skills", [None]), ("fallback", "  ")):
            with self.subTest(field=field):
                self.assertTrue(VALIDATE.validate_companion_registry(self.changed(field, value)))

    def copied_repository(self, directory):
        root = Path(directory)
        shutil.copytree(SKILL, root / "skills/second-founder", ignore=shutil.ignore_patterns("__pycache__"))
        return root

    def test_repository_validation_checks_registry_and_its_documentation_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.copied_repository(directory)
            self.assertEqual(VALIDATE.validate_repository(root), [])
            doc = root / "skills/second-founder/references/capabilities.md"
            original = doc.read_text(encoding="utf-8")
            doc.write_text(original.replace("../assets/companion-registry.json", "../assets/project-profile.json"), encoding="utf-8")
            self.assertTrue(any("must link the companion registry" in error for error in VALIDATE.validate_repository(root)))
            doc.write_text(original, encoding="utf-8")
            registry_path = root / "skills/second-founder/assets/companion-registry.json"
            registry_path.write_text(json.dumps(self.changed("ref", "main")), encoding="utf-8")
            self.assertTrue(any("pinned" in error for error in VALIDATE.validate_repository(root)))
            registry_path.unlink()
            self.assertTrue(any("missing companion registry" in error for error in VALIDATE.validate_repository(root)))

    def test_installation_routing_does_not_grant_installation_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.copied_repository(directory)
            template = root / "skills/second-founder/assets/project-profile.json"
            profile = json.loads(template.read_text(encoding="utf-8"))
            self.assertEqual(profile["setup_status"], "unconfigured")
            self.assertEqual(profile["capabilities"]["installation_policy"], "on_demand")
            self.assertEqual(profile["capabilities"]["registry_file"], "capabilities.json")
            self.assertIsNone(profile["authority"]["source"])
            self.assertFalse(profile["automation"]["enabled"])
            profile["authority"]["allowed_categories"].append("skill_installation")
            template.write_text(json.dumps(profile), encoding="utf-8")
            self.assertTrue(any("must not grant" in error for error in VALIDATE.validate_repository(root)))

    def test_template_cannot_enable_bulk_installs_or_bind_an_arbitrary_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.copied_repository(directory)
            template = root / "skills/second-founder/assets/project-profile.json"
            profile = json.loads(template.read_text(encoding="utf-8"))
            profile["capabilities"] = {"installation_policy": "all", "registry_file": "../other.json"}
            template.write_text(json.dumps(profile), encoding="utf-8")
            errors = VALIDATE.validate_repository(root)
            self.assertTrue(any("capabilities.installation_policy" in error for error in errors), errors)
            self.assertTrue(any("capabilities.registry_file" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
