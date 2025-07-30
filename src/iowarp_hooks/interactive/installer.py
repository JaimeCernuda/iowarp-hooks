"""Interactive installation system for hooks with complex setup requirements."""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm

from .paths import InstallationPath, PathConfig
from .actions import ActionRegistry, ActionContext
from ..installer import HookInstaller
from ..templates import TemplateProcessor

console = Console()


class InteractiveInstaller:
    """Handles interactive hook installations with complex setup flows."""
    
    def __init__(
        self,
        hook_name: str,
        hook_config: Dict[str, Any],
        hook_path: Path,
        target: str,
        install_type: str,
        force: bool = False
    ):
        self.hook_name = hook_name
        self.hook_config = hook_config
        self.hook_path = hook_path
        self.target = target
        self.install_type = install_type
        self.force = force
        
        self.template_processor = TemplateProcessor()
        self.standard_installer = HookInstaller(target, install_type)
        
        # Parse interactive config
        self.interactive_config = hook_config.get('interactive_install', {})
        self.pre_install_prompt = self.interactive_config.get('pre_install_prompt', '')
        self.paths = self._parse_paths()
    
    def _parse_paths(self) -> Dict[str, PathConfig]:
        """Parse path configurations from hook config."""
        paths = {}
        paths_config = self.interactive_config.get('paths', {})
        
        for path_name, path_data in paths_config.items():
            paths[path_name] = PathConfig.from_dict(path_data)
        
        return paths
    
    def run(self) -> bool:
        """Execute the interactive installation flow."""
        try:
            # Show pre-install prompt
            if self.pre_install_prompt:
                console.print()
                console.print(self.pre_install_prompt)
                console.print()
            
            # Present path choices
            path_choice = self._get_user_path_choice()
            if not path_choice:
                return False
            
            selected_path_name, selected_path = path_choice
            
            # Collect parameters based on path type
            inputs = self._collect_parameters(selected_path.path_type, selected_path_name)
            
            # Execute path actions
            if not self._execute_path_actions(selected_path, inputs):
                return False
            
            # Run standard hook installation if not exiting
            if selected_path.path_type != InstallationPath.EXIT:
                return self._run_standard_installation(inputs)
            
            return True
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Installation cancelled by user[/yellow]")
            return False
        except Exception as e:
            console.print(f"[red]Installation failed: {e}[/red]")
            return False
    
    def _get_user_path_choice(self) -> Optional[tuple[str, PathConfig]]:
        """Present path choices to user and get selection."""
        if not self.paths:
            console.print("[red]No installation paths configured[/red]")
            return None
        
        console.print("[bold]What do you want to do?[/bold]")
        
        # Create numbered choices
        path_items = list(self.paths.items())
        for i, (path_name, path_config) in enumerate(path_items, 1):
            console.print(f"  {i}. {path_config.label}")
        
        console.print()
        
        # Get user choice
        choices = [str(i) for i in range(1, len(path_items) + 1)]
        choice = Prompt.ask("Select option", choices=choices)
        
        # Return selected path name and config
        selected_path_name, selected_path_config = path_items[int(choice) - 1]
        return (selected_path_name, selected_path_config)
    
    def _collect_parameters(self, path_type: InstallationPath, selected_path_name: str = None) -> Dict[str, str]:
        """Collect parameters based on path type."""
        inputs = {}
        input_configs = self.hook_config.get("inputs", {})
        
        # Pre-fill Docker deployment defaults for observability_viz
        if selected_path_name == "docker_deploy" and self.hook_name == "observability_viz":
            inputs["influxdb_token"] = "claude-observability-token"
            inputs["influxdb_url"] = "http://localhost:8086"
            inputs["influxdb_org"] = "events-org"
            inputs["influxdb_bucket"] = "application-events"
            console.print("[dim]ℹ️  Using pre-configured Docker container settings for InfluxDB connection[/dim]")
        
        console.print()
        
        for input_name, input_config in input_configs.items():
            prompt_text = input_config.get("prompt", f"Enter {input_name}")
            default = input_config.get("default")
            required = input_config.get("required", True)
            
            # Determine if we should ask this question
            should_ask = False
            
            if path_type == InstallationPath.FULL:
                # Ask everything
                should_ask = True
            elif path_type == InstallationPath.DEFAULT:
                # Ask only required parameters
                should_ask = required
            elif path_type == InstallationPath.EXIT:
                # Don't ask anything for exit path
                should_ask = False
            
            if should_ask:
                if required:
                    inputs[input_name] = Prompt.ask(prompt_text, default=default)
                else:
                    inputs[input_name] = Prompt.ask(prompt_text, default=default or "")
            else:
                # Use default value for non-asked parameters
                if default is not None:
                    inputs[input_name] = default
        
        return inputs
    
    def _execute_path_actions(self, path_config: PathConfig, inputs: Dict[str, str]) -> bool:
        """Execute actions for the selected path."""
        if not path_config.actions:
            return True
        
        # Create action context
        target_dir = self.standard_installer.get_target_directory()
        context = ActionContext(
            hook_name=self.hook_name,
            hook_path=self.hook_path,
            target_dir=target_dir,
            inputs=inputs,
            template_processor=self.template_processor
        )
        
        # Execute each action
        for path_action in path_config.actions:
            action = ActionRegistry.get_action(path_action.type, **path_action.__dict__)
            if not action:
                console.print(f"[red]Unknown action type: {path_action.type}[/red]")
                return False
            
            if not action.execute(context):
                console.print(f"[red]Action {path_action.type} failed[/red]")
                return False
        
        return True
    
    def _run_standard_installation(self, inputs: Dict[str, str]) -> bool:
        """Run the standard hook installation process."""
        try:
            # Show installation summary if not forced
            if not self.force:
                console.print(f"\n[bold]Installation Summary:[/bold]")
                console.print(f"  Hook Set: {self.hook_name}")
                console.print(f"  Target: {self.target}")
                console.print(f"  Install Type: {self.install_type}")
                console.print(f"  Parameters: {inputs}")
                
                if not Confirm.ask("Proceed with hook installation?"):
                    console.print("Installation cancelled.")
                    return False
            
            # Install the hook
            self.standard_installer.install_hook_set(
                self.hook_path,
                inputs,
                self.template_processor
            )
            
            console.print(f"[green]✅ Successfully installed {self.hook_name} hooks![/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Hook installation failed: {e}[/red]")
            return False