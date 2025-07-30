"""Pluggable action system for interactive installations."""

import os
import shutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console
from ..templates import TemplateProcessor

console = Console()


class InstallationAction(ABC):
    """Base class for installation actions."""
    
    @abstractmethod
    def execute(self, context: 'ActionContext') -> bool:
        """Execute the action. Returns True if successful."""
        pass


class ActionContext:
    """Context passed to actions during execution."""
    
    def __init__(
        self,
        hook_name: str,
        hook_path: Path,
        target_dir: Path,
        inputs: Dict[str, str],
        template_processor: TemplateProcessor
    ):
        self.hook_name = hook_name
        self.hook_path = hook_path
        self.target_dir = target_dir
        self.inputs = inputs
        self.template_processor = template_processor


class ShowMessageAction(InstallationAction):
    """Action to display a message to the user."""
    
    def __init__(self, message: str):
        self.message = message
    
    def execute(self, context: ActionContext) -> bool:
        # Process message template
        processed_message = context.template_processor.process_string(self.message, context.inputs)
        console.print(processed_message)
        return True


class ExitWithMessageAction(InstallationAction):
    """Action to exit installation with a helpful message."""
    
    def __init__(self, message: str):
        self.message = message
    
    def execute(self, context: ActionContext) -> bool:
        processed_message = context.template_processor.process_string(self.message, context.inputs)
        console.print(f"[yellow]{processed_message}[/yellow]")
        sys.exit(0)


class CopyDockerInfrastructureAction(InstallationAction):
    """Action to copy Docker infrastructure files."""
    
    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target
    
    def execute(self, context: ActionContext) -> bool:
        try:
            # Source directory (relative to project root)
            project_root = context.hook_path.parent.parent.parent
            source_dir = project_root / self.source
            
            if not source_dir.exists():
                console.print(f"[red]Error: Source directory {source_dir} not found[/red]")
                return False
            
            # Target directory
            target_dir = context.target_dir / self.target
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy files with template processing
            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(source_dir)
                    target_file = target_dir / rel_path
                    
                    # Ensure parent directory exists
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Process templates in specific files
                    if file_path.suffix in ['.env', '.yml', '.yaml', '.md']:
                        content = context.template_processor.process_file(file_path, context.inputs)
                        with open(target_file, 'w') as f:
                            f.write(content)
                    else:
                        # Copy binary files as-is
                        shutil.copy2(file_path, target_file)
            
            console.print(f"[green]✅ Docker infrastructure deployed to: {target_dir}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Error copying Docker infrastructure: {e}[/red]")
            return False


class ValidatePortsAction(InstallationAction):
    """Action to validate that required ports are available."""
    
    def __init__(self, ports: list):
        self.ports = ports
    
    def execute(self, context: ActionContext) -> bool:
        try:
            import socket
            
            unavailable_ports = []
            for port in self.ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:  # Port is in use
                    unavailable_ports.append(port)
            
            if unavailable_ports:
                console.print(f"[yellow]⚠️  Warning: Ports {unavailable_ports} are already in use[/yellow]")
                console.print("Consider stopping services using these ports or changing configuration")
                return True  # Don't fail, just warn
            
            return True
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not validate ports: {e}[/yellow]")
            return True  # Don't fail on port validation errors


class CheckDockerAction(InstallationAction):
    """Action to check if Docker is available."""
    
    def execute(self, context: ActionContext) -> bool:
        try:
            import subprocess
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                console.print("[green]✅ Docker is available[/green]")
                return True
            else:
                console.print("[red]❌ Docker is not available or not running[/red]")
                console.print("Please install Docker and ensure it's running before proceeding")
                return False
        except FileNotFoundError:
            console.print("[red]❌ Docker is not installed[/red]")
            console.print("Please install Docker before proceeding")
            return False
        except Exception as e:
            console.print(f"[yellow]Warning: Could not check Docker status: {e}[/yellow]")
            return True  # Don't fail on check errors


class ActionRegistry:
    """Registry for installation actions."""
    
    _actions = {
        'show_message': ShowMessageAction,
        'exit_with_message': ExitWithMessageAction,
        'copy_docker_infrastructure': CopyDockerInfrastructureAction,
        'validate_ports': ValidatePortsAction,
        'check_docker': CheckDockerAction,
    }
    
    @classmethod
    def get_action(cls, action_type: str, **kwargs) -> Optional[InstallationAction]:
        """Get an action instance by type."""
        action_class = cls._actions.get(action_type)
        if action_class:
            return action_class(**kwargs)
        return None
    
    @classmethod
    def register_action(cls, action_type: str, action_class: type):
        """Register a new action type."""
        cls._actions[action_type] = action_class