from __future__ import annotations

from dataclasses import dataclass, field

from models.project_model import ProjectModel


@dataclass
class ProjectManager:
    """Manages current project state."""

    current_project: ProjectModel = field(default_factory=ProjectModel)
