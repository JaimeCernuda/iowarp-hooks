"""Installation path types and handling."""

from enum import Enum
from typing import Dict, Any, List
from dataclasses import dataclass


class InstallationPath(Enum):
    """Standard installation path types."""
    FULL = "full"        # Ask all questions including optional parameters
    DEFAULT = "default"  # Ask only required questions, use defaults for optional
    EXIT = "exit"        # Clean exit with no changes


@dataclass
class PathAction:
    """Represents an action to be performed during installation."""
    type: str
    
    def __init__(self, type: str, **kwargs):
        self.type = type
        for key, value in kwargs.items():
            setattr(self, key, value)


@dataclass 
class PathConfig:
    """Configuration for an installation path."""
    label: str
    path_type: InstallationPath
    actions: List[PathAction]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PathConfig':
        """Create PathConfig from dictionary."""
        actions = []
        for action_data in data.get('actions', []):
            action_type = action_data.pop('type')
            actions.append(PathAction(type=action_type, **action_data))
        
        return cls(
            label=data['label'],
            path_type=InstallationPath(data['type']),
            actions=actions
        )