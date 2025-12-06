import hashlib
import json

def gen_release_bundle_hash(environment: str, versions: json) -> str:
    versions = str(versions) + environment
    return hashlib.sha256(versions.encode()).hexdigest()