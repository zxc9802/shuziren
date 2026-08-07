import hashlib
import json
import math
import os
import re
import stat
import tempfile
import unicodedata
from pathlib import Path


PERSONA = "professional-trustworthy-business"
PROVIDER = "heygen-app"
_TOP_LEVEL_FIELDS = frozenset({"version", "defaults", "voices", "identities"})
_DEFAULT_FIELDS = frozenset({"voice", "identity"})
_VOICE_FIELDS = frozenset(
    {
        "provider",
        "voice_id",
        "clone_status",
        "language",
        "speech_compatible",
        "source",
        "source_sha256",
        "authorized",
        "persona",
    }
)
_IDENTITY_FIELDS = frozenset(
    {
        "provider",
        "avatar_group_id",
        "source",
        "source_sha256",
        "authorized",
        "persona",
        "performance_profile",
        "hand_topology",
    }
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_OPAQUE_ID = re.compile(r"[A-Za-z0-9_-]+\Z")
_URI_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
_WINDOWS_ABSOLUTE_PATH = re.compile(r"[A-Za-z]:[\\/]")
_WINDOWS_DEVICE_BASE = re.compile(
    r"(?:CONIN\$|CONOUT\$|CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])\Z",
    re.IGNORECASE,
)
_WINDOWS_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_DRIVE_REMOTE = 4
_SENSITIVE_REFERENCE = re.compile(
    r"(?<![a-z0-9_-])(?:[a-z0-9]+[-_])*"
    r"(?:access[-_]?token|refresh[-_]?token|token|api[-_]?key|authorization|"
    r"cookie|credential|signature)\s*[=:]\s*\S+",
    re.IGNORECASE,
)
_CREDENTIAL_SCHEME_REFERENCE = re.compile(r"(?:basic|bearer)\s+\S+", re.IGNORECASE)
_JWT_REFERENCE = re.compile(r"eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_SECRET_PREFIX_REFERENCE = re.compile(
    r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{8,}", re.IGNORECASE
)


def write_registry(
    path,
    voice_id,
    avatar_group_id,
    voice_source,
    image_source,
    authorized,
    *,
    exclusive=False,
):
    if authorized is not True:
        raise ValueError("authorized must be literal true")
    if type(exclusive) is not bool:
        raise ValueError("exclusive must be a boolean")

    voice_source_reference = _validated_source_input(voice_source, "voice_source")
    image_source_reference = _validated_source_input(image_source, "image_source")
    voice_source_path = _absolute_source_path(
        Path(voice_source_reference), "voice_source"
    )
    image_source_path = _absolute_source_path(
        Path(image_source_reference), "image_source"
    )
    _reject_remote_source_drive(voice_source_path, "voice_source")
    _reject_remote_source_drive(image_source_path, "image_source")
    _reject_source_aliases(voice_source_path, "voice_source")
    _reject_source_aliases(image_source_path, "image_source")
    voice_sha256 = _hash_source_file(voice_source_path, "voice_source")
    image_sha256 = _hash_source_file(image_source_path, "image_source")
    registry = {
        "version": 2,
        "defaults": {"voice": "voice1", "identity": "image1"},
        "voices": {
            "voice1": {
                "provider": PROVIDER,
                "voice_id": voice_id,
                "clone_status": "complete",
                "language": "zh",
                "speech_compatible": True,
                "source": voice_source_reference,
                "source_sha256": voice_sha256,
                "authorized": True,
                "persona": PERSONA,
            }
        },
        "identities": {
            "image1": {
                "provider": PROVIDER,
                "avatar_group_id": avatar_group_id,
                "source": image_source_reference,
                "source_sha256": image_sha256,
                "authorized": True,
                "persona": PERSONA,
                "performance_profile": "business-human-1",
                "hand_topology": "separated",
            }
        },
    }
    _validate_registry(registry)
    contents = (
        json.dumps(
            registry,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    registry_path = Path(path)
    if exclusive:
        _atomic_create(registry_path, contents)
    else:
        _atomic_replace(registry_path, contents)


def load_registry(path):
    registry_path = Path(path)
    try:
        contents = registry_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise ValueError(f"asset registry file not found: {registry_path}") from error
    except (OSError, UnicodeError) as error:
        raise ValueError(f"could not read asset registry: {registry_path}") from error
    try:
        registry = json.loads(contents, object_pairs_hook=_reject_duplicate_object_keys)
    except json.JSONDecodeError as error:
        raise ValueError(f"malformed JSON in asset registry: {registry_path}") from error
    _validate_registry(registry)
    return registry


def resolve_assets(registry, *, voice_alias=None, identity_alias=None):
    _validate_registry(registry)
    selected_voice_alias = _selected_alias(
        voice_alias, registry["defaults"]["voice"], "voice_alias"
    )
    selected_image_alias = _selected_alias(
        identity_alias, registry["defaults"]["identity"], "identity_alias"
    )
    voice = _selected_asset(registry["voices"], selected_voice_alias, "voices")
    identity = _selected_asset(
        registry["identities"], selected_image_alias, "identities"
    )
    return {
        "voice_alias": selected_voice_alias,
        "image_alias": selected_image_alias,
        "voice": voice,
        "identity": identity,
    }


def _selected_alias(requested, default, field):
    if requested is None:
        return default
    if not isinstance(requested, str) or not requested.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return requested


def _selected_asset(collection, alias, section):
    asset = collection.get(alias)
    if type(asset) is not dict:
        raise ValueError(f"{section}.{alias} is missing")
    return asset


def _validate_registry(registry):
    _require_standard_json(registry, "asset registry")
    if type(registry) is not dict:
        raise ValueError("asset registry must be a JSON object")
    _require_exact_fields(registry, _TOP_LEVEL_FIELDS, "top-level")
    if type(registry["version"]) is not int or registry["version"] != 2:
        raise ValueError("asset registry version must be 2")

    defaults = registry["defaults"]
    voices = registry["voices"]
    identities = registry["identities"]
    if type(defaults) is not dict:
        raise ValueError("defaults must be a JSON object")
    if type(voices) is not dict:
        raise ValueError("voices must be a JSON object")
    if type(identities) is not dict:
        raise ValueError("identities must be a JSON object")
    _require_exact_fields(defaults, _DEFAULT_FIELDS, "defaults")

    voice_alias = _require_alias(defaults["voice"], "defaults.voice")
    identity_alias = _require_alias(defaults["identity"], "defaults.identity")
    if voice_alias not in voices:
        raise ValueError(f"voices.{voice_alias} is missing")
    if identity_alias not in identities:
        raise ValueError(f"identities.{identity_alias} is missing")

    for alias, voice in voices.items():
        _require_alias(alias, "voices alias")
        _validate_voice(voice, f"voices.{alias}")
    for alias, identity in identities.items():
        _require_alias(alias, "identities alias")
        _validate_identity(identity, f"identities.{alias}")


def _validate_voice(voice, prefix):
    if type(voice) is not dict:
        raise ValueError(f"{prefix} must be a JSON object")
    _require_exact_fields(voice, _VOICE_FIELDS, prefix)
    _require_fixed(voice["provider"], PROVIDER, f"{prefix}.provider")
    _validate_opaque_id(voice["voice_id"], f"{prefix}.voice_id")
    _require_fixed(voice["clone_status"], "complete", f"{prefix}.clone_status")
    _require_fixed(voice["language"], "zh", f"{prefix}.language")
    if voice["speech_compatible"] is not True:
        raise ValueError(f"{prefix}.speech_compatible must be literal true")
    _validate_local_source(voice["source"], f"{prefix}.source")
    _validate_sha256(voice["source_sha256"], f"{prefix}.source_sha256")
    if voice["authorized"] is not True:
        raise ValueError(f"{prefix}.authorized must be literal true")
    _require_fixed(voice["persona"], PERSONA, f"{prefix}.persona")


def _validate_identity(identity, prefix):
    if type(identity) is not dict:
        raise ValueError(f"{prefix} must be a JSON object")
    _require_exact_fields(identity, _IDENTITY_FIELDS, prefix)
    _require_fixed(identity["provider"], PROVIDER, f"{prefix}.provider")
    _validate_opaque_id(identity["avatar_group_id"], f"{prefix}.avatar_group_id")
    _validate_local_source(identity["source"], f"{prefix}.source")
    _validate_sha256(identity["source_sha256"], f"{prefix}.source_sha256")
    if identity["authorized"] is not True:
        raise ValueError(f"{prefix}.authorized must be literal true")
    _require_fixed(identity["persona"], PERSONA, f"{prefix}.persona")
    _require_fixed(
        identity["performance_profile"],
        "business-human-1",
        f"{prefix}.performance_profile",
    )
    _require_fixed(identity["hand_topology"], "separated", f"{prefix}.hand_topology")


def _require_exact_fields(value, expected, label):
    actual = set(value)
    unknown = actual - expected
    if unknown:
        field = sorted(unknown)[0]
        raise ValueError(f"{label} contains unknown field: {field}")
    missing = expected - actual
    if missing:
        field = sorted(missing)[0]
        raise ValueError(f"{label}.{field} is required")


def _require_alias(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{field} must not contain surrounding whitespace")
    return value


def _require_fixed(value, expected, field):
    if value != expected or type(value) is not type(expected):
        raise ValueError(f"{field} must be {expected!r}")


def _validate_sha256(value, field):
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase 64-character SHA-256")


def _validate_opaque_id(value, field):
    if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value):
        raise ValueError(
            f"{field} must be an opaque ID using only ASCII letters, digits, _, or -"
        )
    if _contains_credentials(value):
        raise ValueError(f"{field} must not contain credentials")


def _validate_local_source(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty local source reference")
    if value != value.strip() or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        raise ValueError(f"{field} must not contain surrounding whitespace or controls")
    normalized = value.replace("\\", "/")
    if normalized.startswith("//"):
        raise ValueError(f"{field} must be a local source reference, not network/device")
    components = re.split(r"[\\/]", value)
    if any(component == ".." for component in components):
        raise ValueError(f"{field} must not contain parent traversal")
    if any(_is_windows_device_component(component) for component in components):
        raise ValueError(f"{field} must be a local source reference, not a device")
    if _URI_SCHEME.match(value) and not _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError(f"{field} must be a local source reference, not a URL")
    if _contains_credentials(value):
        raise ValueError(f"{field} must not contain credentials")


def _contains_credentials(value):
    return any(
        pattern.search(value)
        for pattern in (
            _SENSITIVE_REFERENCE,
            _CREDENTIAL_SCHEME_REFERENCE,
            _JWT_REFERENCE,
            _SECRET_PREFIX_REFERENCE,
        )
    )


def _is_windows_device_component(component):
    without_stream = component.split(":", 1)[0].rstrip(" .")
    base = without_stream.split(".", 1)[0].rstrip(" .")
    return bool(_WINDOWS_DEVICE_BASE.fullmatch(base))


def _validated_source_input(value, field):
    try:
        reference = os.fspath(value)
    except TypeError as error:
        raise ValueError(f"{field} must be a local source path") from error
    if not isinstance(reference, str):
        raise ValueError(f"{field} must be a local source path")
    _validate_local_source(reference, field)
    return reference


def _absolute_source_path(source, field):
    if source.drive and not source.is_absolute():
        raise ValueError(f"{field} must not use a drive-relative path")
    return source if source.is_absolute() else Path.cwd() / source


def _reject_remote_source_drive(source, field):
    if not _is_windows():
        return
    root = source.anchor.replace("/", "\\")
    if not root.endswith("\\"):
        root += "\\"
    if _get_windows_drive_type(root) == _DRIVE_REMOTE:
        raise ValueError(f"{field} must be a local source path")


def _is_windows():
    return os.name == "nt"


def _get_windows_drive_type(root):
    import ctypes

    get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
    get_drive_type.argtypes = [ctypes.c_wchar_p]
    get_drive_type.restype = ctypes.c_uint
    return get_drive_type(root)


def _reject_source_aliases(source, field):
    # Static preflight only; callers must keep local source paths stable while hashing.
    current = Path(source.anchor)
    parts = source.parts[1:] if source.anchor else source.parts
    for component in parts:
        current /= component
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        except OSError as error:
            raise ValueError(f"could not inspect {field}: {source}") from error
        if stat.S_ISLNK(metadata.st_mode) or (
            getattr(metadata, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT
        ):
            raise ValueError(f"{field} must not contain a symlink or reparse point")


def _require_standard_json(value, label, active=None):
    value_type = type(value)
    if value is None or value_type in {bool, int, str}:
        return
    if value_type is float:
        if math.isfinite(value):
            return
        raise ValueError(f"{label} must contain only standard JSON values")
    if value_type not in {dict, list}:
        raise ValueError(f"{label} must contain only standard JSON values")

    if active is None:
        active = set()
    container_id = id(value)
    if container_id in active:
        raise ValueError(f"{label} must contain only standard JSON values")
    active.add(container_id)
    try:
        if value_type is dict:
            for key, nested in value.items():
                if type(key) is not str:
                    raise ValueError(f"{label} must contain only standard JSON values")
                _require_standard_json(nested, label, active)
        else:
            for nested in value:
                _require_standard_json(nested, label, active)
    finally:
        active.remove(container_id)


def _hash_source_file(source, field):
    try:
        if not source.is_file():
            raise ValueError(f"{field} must be an existing local file: {source}")
        digest = hashlib.sha256()
        with source.open("rb") as file:
            if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
                raise ValueError(f"{field} must be an existing local file: {source}")
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except ValueError:
        raise
    except OSError as error:
        raise ValueError(f"could not read {field}: {source}") from error


def _atomic_create(destination, contents):
    temporary = _write_temporary(destination, contents)
    try:
        os.link(temporary, destination)
    finally:
        _best_effort_unlink(temporary)


def _atomic_replace(destination, contents):
    temporary = _write_temporary(destination, contents)
    try:
        os.replace(temporary, destination)
    finally:
        _best_effort_unlink(temporary)


def _write_temporary(destination, contents):
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(raw_path)
    try:
        stream = os.fdopen(descriptor, "wb")
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        _best_effort_unlink(temporary)
        raise

    try:
        with stream as file:
            file.write(contents)
            file.flush()
            os.fsync(file.fileno())
    except Exception:
        _best_effort_unlink(temporary)
        raise
    return temporary


def _best_effort_unlink(path):
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _reject_duplicate_object_keys(pairs):
    value = {}
    for key, nested in pairs:
        if key in value:
            raise ValueError(f"duplicate asset registry field: {key}")
        value[key] = nested
    return value
