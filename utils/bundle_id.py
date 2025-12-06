import hashlib
import json
from typing import Mapping


def gen_release_bundle_hash(environment: str, versions: Mapping[str, str]) -> str:
    """
    Generate a deterministic hash for a release bundle by hashing a stable,
    sorted JSON representation of versions alongside the environment.
    """
    payload = {
        "environment": environment,
        "versions": versions,
    }
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode()).hexdigest()
