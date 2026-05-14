from dataclasses import dataclass, field

from models.annotation import Annotation


@dataclass
class ProjectModel:
    annotations: list[Annotation] = field(default_factory=list)
