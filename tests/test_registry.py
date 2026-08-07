import hashlib
import importlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.dhflow import registry as registry_module
from scripts.dhflow.registry import load_registry, resolve_assets, write_registry


ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = ROOT / "scripts" / "init_asset_registry.py"
SHA_A = "a" * 64
SHA_B = "b" * 64


def _valid_registry():
    return {
        "version": 2,
        "defaults": {"voice": "voice1", "identity": "image1"},
        "voices": {
            "voice1": {
                "provider": "heygen-app",
                "voice_id": "voice_abc123",
                "clone_status": "complete",
                "language": "zh",
                "speech_compatible": True,
                "source": "authorized-voice.wav",
                "source_sha256": SHA_A,
                "authorized": True,
                "persona": "professional-trustworthy-business",
            }
        },
        "identities": {
            "image1": {
                "provider": "heygen-app",
                "avatar_group_id": "group_abc123",
                "source": "authorized-image.png",
                "source_sha256": SHA_B,
                "authorized": True,
                "persona": "professional-trustworthy-business",
                "performance_profile": "business-human-1",
                "hand_topology": "separated",
            }
        },
    }


class AssetRegistryTests(unittest.TestCase):
    def test_loads_and_resolves_valid_heygen_app_registry_v2(self):
        registry_path = self._write_registry_json(_valid_registry())

        assets = resolve_assets(load_registry(registry_path))

        self.assertEqual("voice1", assets["voice_alias"])
        self.assertEqual("image1", assets["image_alias"])
        self.assertEqual("voice_abc123", assets["voice"]["voice_id"])
        self.assertEqual("group_abc123", assets["identity"]["avatar_group_id"])

    def test_resolves_explicit_valid_aliases(self):
        registry = _valid_registry()
        registry["voices"]["voice2"] = {
            **registry["voices"]["voice1"],
            "voice_id": "voice_def456",
            "source": "authorized-voice-2.wav",
            "source_sha256": "c" * 64,
        }
        registry["identities"]["image2"] = {
            **registry["identities"]["image1"],
            "avatar_group_id": "group_def456",
            "source": "authorized-image-2.png",
            "source_sha256": "d" * 64,
        }

        assets = resolve_assets(
            registry, voice_alias="voice2", identity_alias="image2"
        )

        self.assertEqual("voice_def456", assets["voice"]["voice_id"])
        self.assertEqual("group_def456", assets["identity"]["avatar_group_id"])

    def test_load_registry_accepts_utf8_bom(self):
        registry_path = self._write_registry_json(_valid_registry(), encoding="utf-8-sig")

        registry = load_registry(registry_path)

        self.assertEqual(2, registry["version"])

    def test_duplicate_json_keys_are_rejected_at_any_nesting_level(self):
        serialized = json.dumps(_valid_registry(), ensure_ascii=False)
        cases = (
            serialized.replace('"version": 2', '"version": 2, "version": 2', 1),
            serialized.replace(
                '"provider": "heygen-app"',
                '"provider": "heygen-app", "provider": "heygen-app"',
                1,
            ),
        )
        for contents in cases:
            with self.subTest(contents=contents[:80]):
                with tempfile.TemporaryDirectory() as directory:
                    registry_path = Path(directory) / "assets.json"
                    registry_path.write_text(contents, encoding="utf-8")

                    with self.assertRaisesRegex(ValueError, "duplicate"):
                        load_registry(registry_path)

    def test_malformed_json_reports_malformed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "assets.json"
            registry_path.write_text("{not json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "malformed JSON"):
                load_registry(registry_path)

    def test_version_one_and_boolean_version_are_rejected(self):
        for version in (1, True):
            with self.subTest(version=version):
                registry = _valid_registry()
                registry["version"] = version

                with self.assertRaisesRegex(ValueError, "version must be 2"):
                    resolve_assets(registry)

    def test_unknown_fields_are_rejected_at_every_schema_level(self):
        cases = (
            ((), "legacy", "top-level"),
            (("defaults",), "legacy", "defaults"),
            (("voices", "voice1"), "legacy", "voices.voice1"),
            (("identities", "image1"), "legacy", "identities.image1"),
        )
        for path, field, message in cases:
            with self.subTest(path=path):
                registry = _valid_registry()
                target = registry
                for component in path:
                    target = target[component]
                target[field] = "not allowed"

                with self.assertRaisesRegex(ValueError, message):
                    resolve_assets(registry)

    def test_legacy_provider_and_provider_voice_id_are_rejected(self):
        cases = (
            ("provider", "minimax-cn", "provider"),
            ("provider_voice_id", "legacy-voice", "provider_voice_id"),
        )
        for field, value, message in cases:
            with self.subTest(field=field):
                registry = _valid_registry()
                registry["voices"]["voice1"][field] = value

                with self.assertRaisesRegex(ValueError, message):
                    resolve_assets(registry)

    def test_non_heygen_app_identity_provider_is_rejected(self):
        registry = _valid_registry()
        registry["identities"]["image1"]["provider"] = "other"

        with self.assertRaisesRegex(ValueError, "provider"):
            resolve_assets(registry)

    def test_incomplete_clone_and_nonliteral_speech_compatibility_are_rejected(self):
        cases = (
            ("clone_status", "pending", "clone_status"),
            ("speech_compatible", 1, "speech_compatible"),
            ("speech_compatible", "true", "speech_compatible"),
            ("speech_compatible", False, "speech_compatible"),
        )
        for field, value, message in cases:
            with self.subTest(field=field, value=value):
                registry = _valid_registry()
                registry["voices"]["voice1"][field] = value

                with self.assertRaisesRegex(ValueError, message):
                    resolve_assets(registry)

    def test_fixed_profile_fields_are_enforced(self):
        cases = (
            ("voices", "persona", "other", "persona"),
            ("voices", "language", "en", "language"),
            ("identities", "persona", "other", "persona"),
            ("identities", "performance_profile", "other", "performance_profile"),
            ("identities", "hand_topology", "one_visible", "hand_topology"),
        )
        for section, field, value, message in cases:
            with self.subTest(section=section, field=field):
                registry = _valid_registry()
                alias = "voice1" if section == "voices" else "image1"
                registry[section][alias][field] = value

                with self.assertRaisesRegex(ValueError, message):
                    resolve_assets(registry)

    def test_missing_and_invalid_source_hashes_are_rejected(self):
        invalid = (None, "", "A" * 64, "a" * 63, "g" * 64, 1)
        for section, alias in (("voices", "voice1"), ("identities", "image1")):
            missing = _valid_registry()
            del missing[section][alias]["source_sha256"]
            with self.subTest(section=section, value="missing"):
                with self.assertRaisesRegex(ValueError, "source_sha256"):
                    resolve_assets(missing)
            for value in invalid:
                with self.subTest(section=section, value=value):
                    registry = _valid_registry()
                    registry[section][alias]["source_sha256"] = value

                    with self.assertRaisesRegex(ValueError, "source_sha256"):
                        resolve_assets(registry)

    def test_unauthorized_defaults_or_additional_aliases_are_rejected(self):
        cases = []
        for section, alias in (("voices", "voice1"), ("identities", "image1")):
            registry = _valid_registry()
            registry[section][alias]["authorized"] = False
            cases.append(registry)
        registry = _valid_registry()
        registry["voices"]["voice2"] = {
            **registry["voices"]["voice1"],
            "voice_id": "voice_other",
            "authorized": False,
        }
        cases.append(registry)

        for registry in cases:
            with self.subTest(registry=registry):
                with self.assertRaisesRegex(ValueError, "authorized"):
                    resolve_assets(registry)

    def test_missing_or_invalid_aliases_are_rejected(self):
        cases = (
            ({"voice": "missing", "identity": "image1"}, "voices.missing"),
            ({"voice": "voice1", "identity": "missing"}, "identities.missing"),
            ({"voice": "", "identity": "image1"}, "defaults.voice"),
            ({"voice": "voice1", "identity": 1}, "defaults.identity"),
        )
        for defaults, message in cases:
            with self.subTest(defaults=defaults):
                registry = _valid_registry()
                registry["defaults"] = defaults

                with self.assertRaisesRegex(ValueError, message):
                    resolve_assets(registry)

    def test_url_path_and_credential_shaped_ids_are_rejected(self):
        invalid_ids = (
            "",
            "https://example.com/id",
            "data:text/plain,id",
            "//example.com/id",
            "id/path",
            "id\\path",
            "id?query=1",
            "id#fragment",
            "Authorization:Bearer-secret",
            "Bearer secret",
            "api_key=secret",
            "sk-1234567890abcdef",
            "eyJabc.def.ghi",
        )
        for section, alias, field in (
            ("voices", "voice1", "voice_id"),
            ("identities", "image1", "avatar_group_id"),
        ):
            for value in invalid_ids:
                with self.subTest(field=field, value=value):
                    registry = _valid_registry()
                    registry[section][alias][field] = value

                    with self.assertRaisesRegex(ValueError, field):
                        resolve_assets(registry)

    def test_domain_endpoint_and_header_shaped_ids_are_rejected(self):
        invalid_ids = (
            "www.example.com",
            "www.example.com:443",
            "X_Custom:secret",
            "X-Custom:secret",
            "header:value",
        )
        for section, alias, field in (
            ("voices", "voice1", "voice_id"),
            ("identities", "image1", "avatar_group_id"),
        ):
            for value in invalid_ids:
                with self.subTest(field=field, value=value):
                    registry = _valid_registry()
                    registry[section][alias][field] = value

                    with self.assertRaisesRegex(ValueError, field):
                        resolve_assets(registry)

    def test_opaque_ids_accept_underscore_and_hyphen(self):
        registry = _valid_registry()
        registry["voices"]["voice1"]["voice_id"] = "voice_abc123"
        registry["identities"]["image1"]["avatar_group_id"] = "group-abc123"

        assets = resolve_assets(registry)

        self.assertEqual("voice_abc123", assets["voice"]["voice_id"])
        self.assertEqual("group-abc123", assets["identity"]["avatar_group_id"])

    def test_url_and_credential_shaped_sources_are_rejected(self):
        for value in (
            "https://example.com/source.wav",
            "Authorization: Bearer secret",
            "api_key=secret",
        ):
            with self.subTest(value=value):
                registry = _valid_registry()
                registry["voices"]["voice1"]["source"] = value

                with self.assertRaisesRegex(ValueError, "source"):
                    resolve_assets(registry)

    def test_programmatic_nonstandard_and_cyclic_containers_are_rejected(self):
        class DictSubclass(dict):
            pass

        class ListSubclass(list):
            pass

        invalid = (
            DictSubclass(_valid_registry()),
            {**_valid_registry(), "defaults": DictSubclass(_valid_registry()["defaults"])},
            {**_valid_registry(), "voices": (("voice1", {}),)},
            {**_valid_registry(), "identities": ListSubclass([])},
            {**_valid_registry(), 1: "non-string key"},
            {**_valid_registry(), "extra": float("nan")},
        )
        for registry in invalid:
            with self.subTest(type=type(registry).__name__):
                with self.assertRaisesRegex(ValueError, "standard JSON"):
                    resolve_assets(registry)

        cyclic = _valid_registry()
        cyclic["extra"] = cyclic
        with self.assertRaisesRegex(ValueError, "standard JSON"):
            resolve_assets(cyclic)

    def test_write_registry_hashes_existing_sources_and_emits_exact_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source = base / "授权声音.wav"
            image_source = base / "授权肖像.png"
            voice_source.write_bytes(b"voice source bytes")
            image_source.write_bytes(b"image source bytes")
            registry_path = base / "assets.json"

            write_registry(
                registry_path,
                "voice_abc123",
                "group_abc123",
                voice_source,
                image_source,
                True,
            )

            raw = registry_path.read_bytes()
            registry = json.loads(raw.decode("utf-8"))

        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(set(_valid_registry()), set(registry))
        self.assertEqual(
            hashlib.sha256(b"voice source bytes").hexdigest(),
            registry["voices"]["voice1"]["source_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(b"image source bytes").hexdigest(),
            registry["identities"]["image1"]["source_sha256"],
        )
        self.assertEqual(str(voice_source), registry["voices"]["voice1"]["source"])
        self.assertEqual(str(image_source), registry["identities"]["image1"]["source"])
        serialized = raw.decode("utf-8").lower()
        for forbidden in (
            "minimax",
            "provider_voice_id",
            "api_key",
            "authorization",
            "bearer",
            "endpoint",
            "https://",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_write_registry_requires_existing_regular_source_files(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source = base / "voice.wav"
            image_source = base / "image.png"
            voice_source.write_bytes(b"voice")
            image_source.mkdir()
            registry_path = base / "assets.json"

            with self.assertRaisesRegex(ValueError, "image_source"):
                write_registry(
                    registry_path,
                    "voice_abc123",
                    "group_abc123",
                    voice_source,
                    image_source,
                    True,
                )

            self.assertFalse(registry_path.exists())

    def test_write_registry_rejects_network_and_device_sources_before_file_access(self):
        invalid_sources = (
            r"\\server\share\voice.mp3",
            "//server/share/voice.mp3",
            r"\\?\UNC\server\share\voice.mp3",
            r"\\.\PIPE\heygen",
            "//?/UNC/server/share/voice.mp3",
            "//./PIPE/heygen",
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            for argument in ("voice_source", "image_source"):
                for invalid_source in invalid_sources:
                    with self.subTest(argument=argument, source=invalid_source):
                        registry_path = base / f"{argument}.json"
                        arguments = {
                            "voice_source": voice_source,
                            "image_source": image_source,
                        }
                        arguments[argument] = invalid_source
                        with patch.object(
                            registry_module,
                            "_hash_source_file",
                            side_effect=AssertionError("filesystem hash attempted"),
                        ) as hash_file:
                            with patch.object(
                                registry_module.Path,
                                "is_file",
                                side_effect=AssertionError("filesystem stat attempted"),
                            ) as is_file:
                                with patch.object(
                                    registry_module.Path,
                                    "open",
                                    side_effect=AssertionError(
                                        "filesystem open attempted"
                                    ),
                                ) as open_file:
                                    with self.assertRaisesRegex(ValueError, argument):
                                        write_registry(
                                            registry_path,
                                            "voice_abc123",
                                            "group_abc123",
                                            arguments["voice_source"],
                                            arguments["image_source"],
                                            True,
                                        )

                        hash_file.assert_not_called()
                        is_file.assert_not_called()
                        open_file.assert_not_called()
                        self.assertFalse(registry_path.exists())

    def test_write_registry_rejects_windows_reserved_devices_before_file_access(self):
        invalid_sources = (
            "CONIN$",
            "conout$.txt",
            r"folder\CoNiN$.log",
            "folder/ConOut$.data",
            "COM¹",
            "com².txt",
            r"folder\CoM³.log",
            "LPT¹",
            "lpt².txt",
            "folder/LpT³.log",
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            for argument in ("voice_source", "image_source"):
                for invalid_source in invalid_sources:
                    with self.subTest(argument=argument, source=invalid_source):
                        registry_path = base / f"reserved-{argument}.json"
                        arguments = {
                            "voice_source": voice_source,
                            "image_source": image_source,
                        }
                        arguments[argument] = invalid_source
                        with patch.object(
                            registry_module,
                            "_hash_source_file",
                            side_effect=AssertionError("filesystem hash attempted"),
                        ) as hash_file:
                            with patch.object(
                                registry_module.Path,
                                "is_file",
                                side_effect=AssertionError("filesystem stat attempted"),
                            ) as is_file:
                                with patch.object(
                                    registry_module.Path,
                                    "open",
                                    side_effect=AssertionError(
                                        "filesystem open attempted"
                                    ),
                                ) as open_file:
                                    with self.assertRaisesRegex(ValueError, argument):
                                        write_registry(
                                            registry_path,
                                            "voice_abc123",
                                            "group_abc123",
                                            arguments["voice_source"],
                                            arguments["image_source"],
                                            True,
                                        )

                        hash_file.assert_not_called()
                        is_file.assert_not_called()
                        open_file.assert_not_called()
                        self.assertFalse(registry_path.exists())

    def test_write_registry_normalizes_device_components_before_file_access(self):
        invalid_sources = (
            "folder/CON .txt",
            r"folder\con...",
            "folder/ConOut$ .data",
            "folder/COM1 :stream",
            "folder/com¹ .log",
            "folder/LPT2...:stream",
            "folder/lpt³ .txt:stream",
            "folder/NUL. .txt",
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            for argument in ("voice_source", "image_source"):
                for invalid_source in invalid_sources:
                    with self.subTest(argument=argument, source=invalid_source):
                        registry_path = base / f"normalized-{argument}.json"
                        arguments = {
                            "voice_source": voice_source,
                            "image_source": image_source,
                        }
                        arguments[argument] = invalid_source
                        with patch.object(
                            registry_module.Path,
                            "lstat",
                            side_effect=AssertionError("filesystem lstat attempted"),
                        ) as lstat:
                            with patch.object(
                                registry_module,
                                "_hash_source_file",
                                side_effect=AssertionError("filesystem hash attempted"),
                            ) as hash_file:
                                with patch.object(
                                    registry_module.Path,
                                    "is_file",
                                    side_effect=AssertionError(
                                        "filesystem stat attempted"
                                    ),
                                ) as is_file:
                                    with patch.object(
                                        registry_module.Path,
                                        "open",
                                        side_effect=AssertionError(
                                            "filesystem open attempted"
                                        ),
                                    ) as open_file:
                                        with self.assertRaisesRegex(
                                            ValueError, argument
                                        ):
                                            write_registry(
                                                registry_path,
                                                "voice_abc123",
                                                "group_abc123",
                                                arguments["voice_source"],
                                                arguments["image_source"],
                                                True,
                                            )

                        lstat.assert_not_called()
                        hash_file.assert_not_called()
                        is_file.assert_not_called()
                        open_file.assert_not_called()
                        self.assertFalse(registry_path.exists())

    def test_write_registry_rejects_real_symlink_sources_before_open_or_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            actual = base / "actual"
            actual.mkdir()
            voice_source = actual / "voice.wav"
            image_source = actual / "image.png"
            voice_source.write_bytes(b"voice")
            image_source.write_bytes(b"image")
            parent_link = base / "linked-parent"
            final_link = base / "linked-image.png"
            try:
                parent_link.symlink_to(actual, target_is_directory=True)
                final_link.symlink_to(image_source)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"local symlink creation unavailable: {error}")

            cases = (
                (parent_link / "voice.wav", image_source),
                (voice_source, final_link),
            )
            for invalid_voice, invalid_image in cases:
                with self.subTest(source=(str(invalid_voice), str(invalid_image))):
                    registry_path = base / "symlink-assets.json"
                    with patch.object(
                        registry_module,
                        "_hash_source_file",
                        side_effect=AssertionError("filesystem hash attempted"),
                    ) as hash_file:
                        with patch.object(
                            registry_module.Path,
                            "is_file",
                            side_effect=AssertionError("filesystem stat attempted"),
                        ) as is_file:
                            with patch.object(
                                registry_module.Path,
                                "open",
                                side_effect=AssertionError("filesystem open attempted"),
                            ) as open_file:
                                with self.assertRaisesRegex(
                                    ValueError, "symlink|reparse"
                                ):
                                    write_registry(
                                        registry_path,
                                        "voice_abc123",
                                        "group_abc123",
                                        invalid_voice,
                                        invalid_image,
                                        True,
                                    )

                    hash_file.assert_not_called()
                    is_file.assert_not_called()
                    open_file.assert_not_called()
                    self.assertFalse(registry_path.exists())

    def test_write_registry_rejects_windows_reparse_parent_before_open_or_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            _, image_source = self._create_sources(base)
            registry_path = base / "assets.json"
            voice_source = base / "reparse-parent" / "voice.wav"
            reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

            def fake_lstat(path):
                attributes = reparse_attribute if path.name == "reparse-parent" else 0
                return SimpleNamespace(
                    st_mode=stat.S_IFDIR,
                    st_file_attributes=attributes,
                )

            with patch.object(
                registry_module.Path, "lstat", autospec=True, side_effect=fake_lstat
            ):
                with patch.object(
                    registry_module,
                    "_hash_source_file",
                    side_effect=AssertionError("filesystem hash attempted"),
                ) as hash_file:
                    with patch.object(
                        registry_module.Path,
                        "is_file",
                        side_effect=AssertionError("filesystem stat attempted"),
                    ) as is_file:
                        with patch.object(
                            registry_module.Path,
                            "open",
                            side_effect=AssertionError("filesystem open attempted"),
                        ) as open_file:
                            with self.assertRaisesRegex(ValueError, "reparse"):
                                write_registry(
                                    registry_path,
                                    "voice_abc123",
                                    "group_abc123",
                                    voice_source,
                                    image_source,
                                    True,
                                )

            hash_file.assert_not_called()
            is_file.assert_not_called()
            open_file.assert_not_called()
            self.assertFalse(registry_path.exists())

    @unittest.skipUnless(os.name == "nt", "Windows path semantics required")
    def test_write_registry_rejects_mapped_drive_before_filesystem_access(self):
        cases = (
            (r"Z:\mapped\voice.wav", r"C:\local\image.png", "voice_source"),
            (r"C:\local\voice.wav", r"Z:\mapped\image.png", "image_source"),
        )

        def drive_type(root):
            return 4 if root.upper().startswith("Z:") else 3

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for voice_source, image_source, error_field in cases:
                with self.subTest(error_field=error_field):
                    registry_path = base / f"mapped-{error_field}.json"
                    with patch.object(
                        registry_module,
                        "_get_windows_drive_type",
                        side_effect=drive_type,
                    ) as get_drive_type:
                        with patch.object(
                            registry_module.Path,
                            "lstat",
                            side_effect=AssertionError("filesystem lstat attempted"),
                        ) as lstat:
                            with patch.object(
                                registry_module,
                                "_hash_source_file",
                                side_effect=AssertionError("filesystem hash attempted"),
                            ) as hash_file:
                                with patch.object(
                                    registry_module.Path,
                                    "is_file",
                                    side_effect=AssertionError(
                                        "filesystem stat attempted"
                                    ),
                                ) as is_file:
                                    with patch.object(
                                        registry_module.Path,
                                        "open",
                                        side_effect=AssertionError(
                                            "filesystem open attempted"
                                        ),
                                    ) as open_file:
                                        with self.assertRaisesRegex(
                                            ValueError, error_field
                                        ) as error:
                                            write_registry(
                                                registry_path,
                                                "voice_abc123",
                                                "group_abc123",
                                                voice_source,
                                                image_source,
                                                True,
                                            )

                    self.assertNotIn(voice_source, str(error.exception))
                    self.assertNotIn(image_source, str(error.exception))
                    self.assertTrue(get_drive_type.called)
                    for call in get_drive_type.call_args_list:
                        self.assertTrue(call.args[0].endswith("\\"))
                    lstat.assert_not_called()
                    hash_file.assert_not_called()
                    is_file.assert_not_called()
                    open_file.assert_not_called()
                    self.assertFalse(registry_path.exists())

    @unittest.skipUnless(os.name == "nt", "Windows path semantics required")
    def test_relative_source_rejects_mapped_current_drive_before_file_access(self):
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "assets.json"
            with patch.object(
                registry_module.Path,
                "cwd",
                return_value=Path(r"Z:\mapped\working"),
            ):
                with patch.object(
                    registry_module,
                    "_get_windows_drive_type",
                    return_value=4,
                ) as get_drive_type:
                    with patch.object(
                        registry_module.Path,
                        "lstat",
                        side_effect=AssertionError("filesystem lstat attempted"),
                    ) as lstat:
                        with patch.object(
                            registry_module,
                            "_hash_source_file",
                            side_effect=AssertionError("filesystem hash attempted"),
                        ) as hash_file:
                            with patch.object(
                                registry_module.Path,
                                "is_file",
                                side_effect=AssertionError("filesystem stat attempted"),
                            ) as is_file:
                                with patch.object(
                                    registry_module.Path,
                                    "open",
                                    side_effect=AssertionError(
                                        "filesystem open attempted"
                                    ),
                                ) as open_file:
                                    with self.assertRaisesRegex(
                                        ValueError, "voice_source"
                                    ) as error:
                                        write_registry(
                                            registry_path,
                                            "voice_abc123",
                                            "group_abc123",
                                            "voice.wav",
                                            "image.png",
                                            True,
                                        )

            self.assertNotIn("voice.wav", str(error.exception))
            self.assertNotIn("image.png", str(error.exception))
            get_drive_type.assert_called_once_with("Z:\\")
            lstat.assert_not_called()
            hash_file.assert_not_called()
            is_file.assert_not_called()
            open_file.assert_not_called()
            self.assertFalse(registry_path.exists())

    @unittest.skipUnless(os.name == "nt", "Windows path semantics required")
    def test_fixed_drive_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            registry_path = base / "assets.json"

            with patch.object(
                registry_module,
                "_get_windows_drive_type",
                return_value=3,
            ) as get_drive_type:
                write_registry(
                    registry_path,
                    "voice_abc123",
                    "group_abc123",
                    voice_source,
                    image_source,
                    True,
                )

            self.assertTrue(registry_path.exists())
            self.assertEqual(2, get_drive_type.call_count)
            for call in get_drive_type.call_args_list:
                self.assertTrue(call.args[0].endswith("\\"))

    def test_non_windows_skips_drive_type_lookup_for_host_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            registry_path = base / "assets.json"
            with patch.object(registry_module, "_is_windows", return_value=False):
                with patch.object(registry_module, "_get_windows_drive_type") as lookup:
                    write_registry(
                        registry_path,
                        "voice_abc123",
                        "group_abc123",
                        voice_source,
                        image_source,
                        True,
                    )

            self.assertTrue(registry_path.exists())
            lookup.assert_not_called()

    def test_registry_accepts_local_drive_and_relative_source_references(self):
        registry = _valid_registry()
        registry["voices"]["voice1"]["source"] = r"C:\authorized\voice.wav"
        registry["identities"]["image1"]["source"] = "assets/image.png"

        assets = resolve_assets(registry)

        self.assertEqual(
            r"C:\authorized\voice.wav", assets["voice"]["source"]
        )
        self.assertEqual("assets/image.png", assets["identity"]["source"])

    def test_write_registry_rejects_unauthorized_and_preserves_target(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            registry_path = base / "assets.json"
            original = b'{"existing": true}\n'
            registry_path.write_bytes(original)

            for authorized in (False, 1, "true"):
                with self.subTest(authorized=authorized):
                    with self.assertRaisesRegex(ValueError, "authorized"):
                        write_registry(
                            registry_path,
                            "voice_abc123",
                            "group_abc123",
                            voice_source,
                            image_source,
                            authorized,
                        )
                    self.assertEqual(original, registry_path.read_bytes())

    def test_write_registry_validation_failure_preserves_target(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            registry_path = base / "assets.json"
            original = b'{"existing": true}\n'
            registry_path.write_bytes(original)

            with self.assertRaisesRegex(ValueError, "voice_id"):
                write_registry(
                    registry_path,
                    "https://example.com/voice",
                    "group_abc123",
                    voice_source,
                    image_source,
                    True,
                )

            self.assertEqual(original, registry_path.read_bytes())

    def test_exclusive_write_publishes_complete_temp_without_writing_final_directly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            registry_path = base / "assets.json"
            real_link = os.link
            observed = []

            def observe_publish(temporary, destination):
                self.assertNotEqual(registry_path, Path(temporary))
                self.assertEqual(registry_path, Path(destination))
                self.assertFalse(registry_path.exists())
                observed.append(Path(temporary).read_bytes())
                real_link(temporary, destination)

            with patch.object(
                registry_module.os, "link", side_effect=observe_publish
            ) as publish:
                write_registry(
                    registry_path,
                    "voice_abc123",
                    "group_abc123",
                    voice_source,
                    image_source,
                    True,
                    exclusive=True,
                )

            publish.assert_called_once()
            self.assertEqual([registry_path.read_bytes()], observed)
            self.assertEqual([], list(base.glob(".assets.json.*.tmp")))

    def test_exclusive_write_preserves_existing_target_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            registry_path = base / "assets.json"
            original = b'{"existing": true}\n'
            registry_path.write_bytes(original)

            with self.assertRaises(FileExistsError):
                write_registry(
                    registry_path,
                    "voice_abc123",
                    "group_abc123",
                    voice_source,
                    image_source,
                    True,
                    exclusive=True,
                )

            self.assertEqual(original, registry_path.read_bytes())
            self.assertEqual([], list(base.glob(".assets.json.*.tmp")))

    def test_exclusive_publish_failure_leaves_target_absent_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            registry_path = base / "assets.json"

            with patch.object(
                registry_module.os, "link", side_effect=OSError("publish failed")
            ):
                with self.assertRaisesRegex(OSError, "publish failed"):
                    write_registry(
                        registry_path,
                        "voice_abc123",
                        "group_abc123",
                        voice_source,
                        image_source,
                        True,
                        exclusive=True,
                    )

            self.assertFalse(registry_path.exists())
            self.assertEqual([], list(base.glob(".assets.json.*.tmp")))

    def test_exclusive_publish_never_deletes_concurrent_target(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            registry_path = base / "assets.json"
            competing = b'{"competing": true}\n'

            def create_competing_target(temporary, destination):
                Path(destination).write_bytes(competing)
                raise FileExistsError("target won the race")

            with patch.object(
                registry_module.os, "link", side_effect=create_competing_target
            ):
                with self.assertRaises(FileExistsError):
                    write_registry(
                        registry_path,
                        "voice_abc123",
                        "group_abc123",
                        voice_source,
                        image_source,
                        True,
                        exclusive=True,
                    )

            self.assertEqual(competing, registry_path.read_bytes())
            self.assertEqual([], list(base.glob(".assets.json.*.tmp")))

    def test_publish_failure_is_not_masked_by_temp_cleanup_failure(self):
        for exclusive in (True, False):
            with self.subTest(exclusive=exclusive):
                with tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    voice_source, image_source = self._create_sources(base)
                    registry_path = base / "assets.json"
                    original_target = b'{"existing": true}\n'
                    registry_path.write_bytes(original_target)
                    publish_error = (
                        FileExistsError("publish failed")
                        if exclusive
                        else OSError("replace failed")
                    )
                    publish_name = "link" if exclusive else "replace"
                    caught = None

                    with patch.object(
                        registry_module.os, publish_name, side_effect=publish_error
                    ):
                        with patch.object(
                            registry_module.Path,
                            "unlink",
                            side_effect=PermissionError("cleanup failed"),
                        ):
                            try:
                                write_registry(
                                    registry_path,
                                    "voice_abc123",
                                    "group_abc123",
                                    voice_source,
                                    image_source,
                                    True,
                                    exclusive=exclusive,
                                )
                            except OSError as error:
                                caught = error

                    self.assertIs(publish_error, caught)
                    self.assertEqual(original_target, registry_path.read_bytes())

    def test_successful_publish_is_not_reported_failed_when_temp_cleanup_fails(self):
        for exclusive in (True, False):
            with self.subTest(exclusive=exclusive):
                with tempfile.TemporaryDirectory() as directory:
                    base = Path(directory)
                    voice_source, image_source = self._create_sources(base)
                    registry_path = base / "assets.json"
                    real_publish = os.link if exclusive else os.replace
                    publish_name = "link" if exclusive else "replace"

                    def publish(temporary, destination):
                        real_publish(temporary, destination)

                    with patch.object(
                        registry_module.os, publish_name, side_effect=publish
                    ):
                        with patch.object(
                            registry_module.Path,
                            "unlink",
                            side_effect=PermissionError("cleanup failed"),
                        ):
                            write_registry(
                                registry_path,
                                "voice_abc123",
                                "group_abc123",
                                voice_source,
                                image_source,
                                True,
                                exclusive=exclusive,
                            )

                    registry = json.loads(registry_path.read_text(encoding="utf-8"))
                    self.assertEqual(2, registry["version"])

    def test_fdopen_failure_closes_raw_fd_before_cleanup_and_preserves_error(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            voice_source, image_source = self._create_sources(base)
            registry_path = base / "assets.json"
            original_target = b'{"existing": true}\n'
            registry_path.write_bytes(original_target)
            original_error = OSError("fdopen failed")
            real_close = os.close
            closed_descriptors = []

            def record_close(descriptor):
                closed_descriptors.append(descriptor)
                real_close(descriptor)

            caught = None
            with patch.object(
                registry_module.os, "fdopen", side_effect=original_error
            ):
                with patch.object(
                    registry_module.os, "close", side_effect=record_close
                ):
                    try:
                        write_registry(
                            registry_path,
                            "voice_abc123",
                            "group_abc123",
                            voice_source,
                            image_source,
                            True,
                            exclusive=True,
                        )
                    except OSError as error:
                        caught = error

            self.assertIs(original_error, caught)
            self.assertEqual(1, len(closed_descriptors))
            self.assertEqual(original_target, registry_path.read_bytes())
            self.assertEqual([], list(base.glob(".assets.json.*.tmp")))

    def _write_registry_json(self, registry, encoding="utf-8"):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        registry_path = Path(directory.name) / "assets.json"
        registry_path.write_text(
            json.dumps(registry, ensure_ascii=False), encoding=encoding
        )
        return registry_path

    @staticmethod
    def _create_sources(base):
        voice_source = base / "voice.wav"
        image_source = base / "image.png"
        voice_source.write_bytes(b"voice")
        image_source.write_bytes(b"image")
        return voice_source, image_source


class InitAssetRegistryCliTests(unittest.TestCase):
    def test_cli_help_exposes_only_local_asset_inputs(self):
        result = subprocess.run(
            [sys.executable, str(INIT_SCRIPT), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        for option in (
            "--out",
            "--voice-id",
            "--avatar-group-id",
            "--voice-source",
            "--image-source",
            "--authorized",
            "--force",
        ):
            self.assertIn(option, result.stdout)
        for forbidden in ("minimax", "api-key", "endpoint", "url"):
            self.assertNotIn(forbidden, result.stdout.lower())

    def test_cli_refuses_existing_file_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output_path = base / "assets.json"
            output_path.write_text('{"existing": true}', encoding="utf-8")
            original = output_path.read_bytes()

            result = self._run_cli(output_path, base)

            self.assertNotEqual(0, result.returncode)
            self.assertEqual(original, output_path.read_bytes())

    def test_cli_force_overwrites_and_emits_valid_v2_json(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output_path = base / "nested" / "assets.json"
            output_path.parent.mkdir()
            output_path.write_text('{"existing": true}', encoding="utf-8")

            result = self._run_cli(output_path, base, "--force")

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(str(output_path), result.stdout.strip())
            registry = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(2, registry["version"])
        self.assertEqual("voice_abc123", registry["voices"]["voice1"]["voice_id"])
        self.assertEqual(
            "group_abc123",
            registry["identities"]["image1"]["avatar_group_id"],
        )

    def test_cli_missing_source_file_preserves_existing_target_with_force(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output_path = base / "assets.json"
            output_path.write_bytes(b'{"existing": true}\n')
            original = output_path.read_bytes()
            image_source = base / "image.png"
            image_source.write_bytes(b"image")

            result = subprocess.run(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--out",
                    str(output_path),
                    "--voice-id",
                    "voice_abc123",
                    "--avatar-group-id",
                    "group_abc123",
                    "--voice-source",
                    str(base / "missing.wav"),
                    "--image-source",
                    str(image_source),
                    "--authorized",
                    "--force",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("voice_source", result.stderr)
            self.assertEqual(original, output_path.read_bytes())

    def test_cli_stdout_is_strict_utf8_without_python_encoding_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output_path = base / "中文目录" / "资产.json"
            environment = os.environ.copy()
            environment.pop("PYTHONUTF8", None)
            environment.pop("PYTHONIOENCODING", None)

            result = subprocess.run(
                [sys.executable, str(INIT_SCRIPT), *self._cli_args(output_path, base)],
                cwd=ROOT,
                capture_output=True,
                text=False,
                check=False,
                env=environment,
            )

            stdout = result.stdout.decode("utf-8", errors="strict")
            stderr = result.stderr.decode("utf-8", errors="strict")

        self.assertEqual(0, result.returncode, stderr)
        self.assertEqual(str(output_path), stdout.strip())

    def test_cli_non_force_creation_is_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output_path = base / "nested" / "assets.json"
            module = self._load_cli_module()
            original_mkdir = Path.mkdir

            def create_competing_file(path, *args, **kwargs):
                result = original_mkdir(path, *args, **kwargs)
                if path == output_path.parent:
                    output_path.write_text('{"existing": true}', encoding="utf-8")
                return result

            with patch.object(module.Path, "mkdir", new=create_competing_file):
                with patch.object(
                    sys,
                    "argv",
                    ["init_asset_registry.py", *self._cli_args(output_path, base)],
                ):
                    with self.assertRaisesRegex(SystemExit, "refusing to overwrite"):
                        module.main()

            self.assertEqual('{"existing": true}', output_path.read_text(encoding="utf-8"))

    @staticmethod
    def _run_cli(output_path, base, *extra_args):
        return subprocess.run(
            [
                sys.executable,
                str(INIT_SCRIPT),
                *InitAssetRegistryCliTests._cli_args(output_path, base),
                *extra_args,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            check=False,
        )

    @staticmethod
    def _cli_args(output_path, base):
        voice_source = base / "voice.wav"
        image_source = base / "image.png"
        voice_source.write_bytes(b"voice")
        image_source.write_bytes(b"image")
        return [
            "--out",
            str(output_path),
            "--voice-id",
            "voice_abc123",
            "--avatar-group-id",
            "group_abc123",
            "--voice-source",
            str(voice_source),
            "--image-source",
            str(image_source),
            "--authorized",
        ]

    @staticmethod
    def _load_cli_module():
        scripts_path = str(ROOT / "scripts")
        sys.path.insert(0, scripts_path)
        try:
            sys.modules.pop("init_asset_registry", None)
            return importlib.import_module("init_asset_registry")
        finally:
            sys.path.remove(scripts_path)


if __name__ == "__main__":
    unittest.main()
