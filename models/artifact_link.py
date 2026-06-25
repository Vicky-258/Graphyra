from dataclasses import dataclass


@dataclass
class ArtifactLink:
    source_artifact_id: str
    target_artifact_id: str
