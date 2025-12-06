import hashlib
import json
import logging
from typing import Mapping

logger = logging.getLogger(__name__)


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
    bundle_hash = hashlib.sha256(normalized.encode()).hexdigest()
    logger.info(
        "generated deployment id",
        extra={
            "environment": environment,
            "version_count": len(versions),
            "deployment_id": bundle_hash,
        },
    )
    return bundle_hash
