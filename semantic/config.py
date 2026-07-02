from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class SemanticConfig:
    enabled: bool = True
    provider: str = "sentence-transformers"
    model: str = "all-MiniLM-L6-v2"
    backend: str = "numpy"
    top_k: int = 10
    batch_size: int = 64
    direct_match_weight: float = 1.0
    semantic_match_weight: float = 0.8

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SemanticConfig":
        sem = d.get("semantic", {})
        fus = d.get("fusion", {})
        return cls(
            enabled=sem.get("enabled", True),
            provider=sem.get("provider", "sentence-transformers"),
            model=sem.get("model", "all-MiniLM-L6-v2"),
            backend=sem.get("backend", "numpy"),
            top_k=sem.get("top_k", 10),
            batch_size=sem.get("batch_size", 64),
            direct_match_weight=fus.get("direct_match_weight", 1.0),
            semantic_match_weight=fus.get("semantic_match_weight", 0.8)
        )
