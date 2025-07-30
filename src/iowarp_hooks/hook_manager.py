#!/usr/bin/env python3
"""Main CLI for iowarp-hooks."""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

from .installer import HookInstaller
from .templates import TemplateProcessor
from .interactive import InteractiveInstaller

console = Console()


def get_hooks_directory() -> Path:
    """Get the hooks directory from the package."""
    return Path(__file__).parent.parent.parent / "hooks"


def get_available_hook_sets() -> Dict[str, Dict]:
    """Get all available hook sets and their configurations."""
    hooks_dir = get_hooks_directory()
    hook_sets = {}
    
    if not hooks_dir.exists():
        return hook_sets
    
    for hook_dir in hooks_dir.iterdir():
        if hook_dir.is_dir():
            config_file = hook_dir / "config.yaml"
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)
                    hook_sets[hook_dir.name] = config
                except Exception as e:
                    console.print(f"[red]Error loading config for {hook_dir.name}: {e}[/red]")
    
    return hook_sets


@click.group()
@click.version_option()
def cli():
    """iowarp-hooks: Claude Code hook manager."""
    pass


@cli.command()
def list():
    """List all available hook sets."""
    hook_sets = get_available_hook_sets()
    
    if not hook_sets:
        console.print("[yellow]No hook sets found.[/yellow]")
        return
    
    table = Table(title="Available Hook Sets")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")
    table.add_column("Inputs", style="green")
    table.add_column("Targets", style="blue")
    
    for name, config in hook_sets.items():
        inputs = ", ".join(config.get("inputs", {}).keys())
        targets = ", ".join(config.get("targets", ["claude"]))
        description = config.get("description", "No description")
        
        table.add_row(name, description, inputs, targets)
    
    console.print(table)


@cli.command()
def installed():
    """List currently installed hook sets."""
    # Try local first, then global
    for install_type in ["local", "global"]:
        installer = HookInstaller("claude", install_type)
        target_dir = installer.get_target_directory()
        settings_file = target_dir / "settings.json"
        
        metadata_file = target_dir / ".hook_metadata.json"
        
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            installed_hook_sets = metadata.get("installed_hook_sets", {})
            if installed_hook_sets:
                location = "Local" if install_type == "local" else "Global"
                console.print(f"\n[bold cyan]{location} Installation ({target_dir}):[/bold cyan]")
                
                table = Table(title=f"Installed Hook Sets - {location}")
                table.add_column("Name", style="cyan", no_wrap=True)
                table.add_column("Version", style="green")
                table.add_column("Description", style="magenta")
                table.add_column("Files", style="yellow")
                
                for hook_set_name, hook_info in installed_hook_sets.items():
                    config = hook_info.get("config", {})
                    file_count = len(hook_info.get("installed_files", []))
                    
                    table.add_row(
                        hook_set_name,
                        config.get("version", "N/A"),
                        config.get("description", "No description"),
                        f"{file_count} files"
                    )
                
                console.print(table)
    
    # Check if no installations found
    local_metadata = Path.cwd() / ".claude" / ".hook_metadata.json"
    global_metadata = Path.home() / ".claude" / ".hook_metadata.json"
    
    if not local_metadata.exists() and not global_metadata.exists():
        console.print("[yellow]No hook sets are currently installed.[/yellow]")


@cli.command()
@click.argument("hook_set")
def info(hook_set: str):
    """Show detailed information about a hook set including available parameters."""
    hook_sets = get_available_hook_sets()
    
    if hook_set not in hook_sets:
        console.print(f"[red]Hook set '{hook_set}' not found.[/red]")
        console.print("Available hook sets:")
        for name in hook_sets.keys():
            console.print(f"  - {name}")
        sys.exit(1)
    
    config = hook_sets[hook_set]
    
    console.print(f"\n[bold cyan]Hook Set: {hook_set}[/bold cyan]")
    console.print(f"[bold]Description:[/bold] {config.get('description', 'No description')}")
    console.print(f"[bold]Version:[/bold] {config.get('version', 'N/A')}")
    console.print(f"[bold]Targets:[/bold] {', '.join(config.get('targets', ['claude']))}")
    
    inputs = config.get("inputs", {})
    if inputs:
        console.print(f"\n[bold]Parameters:[/bold]")
        for input_name, input_config in inputs.items():
            flag_name = input_name.replace("_", "-")
            required = input_config.get("required", True)
            default = input_config.get("default")
            description = input_config.get("description", "No description")
            
            status = "[red]required[/red]" if required else f"[green]optional[/green]"
            if default:
                status += f" (default: {default})"
            
            console.print(f"  --{flag_name:20} {status}")
            console.print(f"  {' ' * 22} {description}")
    
    console.print(f"\n[bold]Usage:[/bold]")
    example_params = []
    for input_name, input_config in inputs.items():
        flag_name = input_name.replace("_", "-")
        if input_config.get("required", True):
            example_params.append(f"--{flag_name} <value>")
    
    param_str = " " + " ".join(example_params) if example_params else ""
    console.print(f"  iowarp-hooks install {hook_set} claude local{param_str}")
    console.print(f"  iowarp-hooks install {hook_set} claude global{param_str}")


@cli.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.argument("hook_set")
@click.argument("target", default="claude")
@click.argument("install_type", default="local", type=click.Choice(["local", "global"]))
@click.option("--force", is_flag=True, help="Force installation without confirmation")
@click.pass_context
def install(ctx: click.Context, hook_set: str, target: str, install_type: str, force: bool):
    """Install a hook set.
    
    Usage examples:
      iowarp-hooks install observability_log claude local --project-name my-project
      iowarp-hooks install observability_viz claude local --project-name my-project --influxdb-token mytoken
    """
    hook_sets = get_available_hook_sets()
    
    if hook_set not in hook_sets:
        console.print(f"[red]Hook set '{hook_set}' not found.[/red]")
        console.print("Available hook sets:")
        for name in hook_sets.keys():
            console.print(f"  - {name}")
        sys.exit(1)
    
    config = hook_sets[hook_set]
    
    # Check if this hook uses interactive installation
    if config.get("interactive_install"):
        hooks_path = get_hooks_directory() / hook_set
        interactive_installer = InteractiveInstaller(
            hook_name=hook_set,
            hook_config=config,
            hook_path=hooks_path,
            target=target,
            install_type=install_type,
            force=force
        )
        success = interactive_installer.run()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Standard installation flow for non-interactive hooks
    # Collect input values from CLI flags
    inputs = {}
    input_configs = config.get("inputs", {})
    
    # Parse extra arguments as --parameter-name value pairs
    extra_args = ctx.args
    i = 0
    while i < len(extra_args):
        arg = extra_args[i]
        if arg.startswith("--"):
            # Convert --parameter-name to parameter_name
            param_name = arg[2:].replace("-", "_")
            if i + 1 < len(extra_args) and not extra_args[i + 1].startswith("--"):
                # Next arg is the value
                inputs[param_name] = extra_args[i + 1]
                i += 2
            else:
                # Flag without value (boolean)
                inputs[param_name] = True
                i += 1
        else:
            i += 1
    
    # Interactive prompts for missing inputs
    for input_name, input_config in input_configs.items():
        if input_name not in inputs:
            prompt_text = input_config.get("prompt", f"Enter {input_name}")
            default = input_config.get("default")
            required = input_config.get("required", True)
            
            if required:
                inputs[input_name] = Prompt.ask(prompt_text, default=default)
            else:
                inputs[input_name] = Prompt.ask(prompt_text, default=default or "")
    
    # Interactive target selection if not supported
    supported_targets = config.get("targets", ["claude"])
    if target not in supported_targets:
        console.print(f"[yellow]Target '{target}' not supported by this hook set.[/yellow]")
        console.print("Supported targets:")
        for i, t in enumerate(supported_targets, 1):
            console.print(f"  {i}. {t}")
        
        choice = Prompt.ask("Select target", choices=[str(i) for i in range(1, len(supported_targets) + 1)])
        target = supported_targets[int(choice) - 1]
    
    # Interactive install type selection
    if not force:
        console.print(f"\nInstallation Summary:")
        console.print(f"  Hook Set: {hook_set}")
        console.print(f"  Target: {target}")
        console.print(f"  Install Type: {install_type}")
        console.print(f"  Inputs: {inputs}")
        
        if not Confirm.ask("Proceed with installation?"):
            console.print("Installation cancelled.")
            return
    
    # Perform installation
    installer = HookInstaller(target, install_type)
    template_processor = TemplateProcessor()
    
    try:
        hooks_path = get_hooks_directory() / hook_set
        installer.install_hook_set(hooks_path, inputs, template_processor)
        console.print(f"[green]Successfully installed {hook_set} hooks![/green]")
    except Exception as e:
        console.print(f"[red]Installation failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("hook_set")
@click.option("--target", default="claude", help="Target tool")
@click.option("--install-type", default="local", type=click.Choice(["local", "global"]))
def uninstall(hook_set: str, target: str, install_type: str):
    """Uninstall a hook set."""
    installer = HookInstaller(target, install_type)
    
    try:
        installer.uninstall_hook_set(hook_set)
        console.print(f"[green]Successfully uninstalled {hook_set} hooks![/green]")
    except Exception as e:
        console.print(f"[red]Uninstallation failed: {e}[/red]")
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()