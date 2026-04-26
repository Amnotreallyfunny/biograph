import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

class CacheManager:
    def __init__(self, cache_path: str):
        self.cache_dir = Path(cache_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.cache_dir / "cache_manifest.json"

    def compute_hash(self, node_type: str, params: Dict, input_data: Any) -> str:
        """Generates a deterministic hash for a node execution."""
        payload = {
            "type": node_type,
            "params": params,
            "input": input_data
        }
        # Sort keys to ensure determinism
        encoded = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        manifest = self._load_manifest()
        return manifest.get(key)

    def set(self, key: str, output_data_id: str):
        manifest = self._load_manifest()
        manifest[key] = output_data_id
        self._save_manifest(manifest)

    def _load_manifest(self) -> Dict:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text())
        return {}

    def _save_manifest(self, manifest: Dict):
        self.manifest_path.write_text(json.dumps(manifest, indent=2))
