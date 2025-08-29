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


def get_opencode_plugins_directory() -> Path:
    """Get the OpenCode plugins directory from the package."""
    return Path(__file__).parent.parent.parent / "opencode_plugins"


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


def get_available_opencode_plugins() -> Dict[str, Dict]:
    """Get all available OpenCode plugins and their configurations."""
    plugins_dir = get_opencode_plugins_directory()
    plugins = {}
    
    if not plugins_dir.exists():
        return plugins
    
    for plugin_dir in plugins_dir.iterdir():
        if plugin_dir.is_dir():
            config_file = plugin_dir / "config.yaml"
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)
                    config["type"] = "opencode_plugin"
                    plugins[plugin_dir.name] = config
                except Exception as e:
                    console.print(f"[red]Error loading config for {plugin_dir.name}: {e}[/red]")
    
    return plugins


@click.group()
@click.version_option()
def cli():
    """iowarp-hooks: Claude Code hook manager."""
    pass


@cli.command()
def list():
    """List all available hook sets and OpenCode plugins."""
    hook_sets = get_available_hook_sets()
    opencode_plugins = get_available_opencode_plugins()
    
    # Combine hook sets and plugins
    all_items = {}
    for name, config in hook_sets.items():
        config["type"] = "claude_hook"
        all_items[name] = config
    
    for name, config in opencode_plugins.items():
        all_items[name] = config
    
    if not all_items:
        console.print("[yellow]No hook sets or plugins found.[/yellow]")
        return
    
    table = Table(title="Available Hook Sets and Plugins")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="red")
    table.add_column("Description", style="magenta")
    table.add_column("Version", style="green")
    table.add_column("Category", style="blue")
    
    for name, config in all_items.items():
        item_type = config.get("type", "unknown")
        description = config.get("description", "No description")
        version = config.get("version", "N/A")
        category = config.get("category", "general")
        
        table.add_row(name, item_type, description, version, category)
    
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
@click.argument("item_name")
def info(item_name: str):
    """Show detailed information about a hook set or OpenCode plugin including available parameters."""
    hook_sets = get_available_hook_sets()
    opencode_plugins = get_available_opencode_plugins()
    
    # Check if it's a hook set or plugin
    if item_name in hook_sets:
        config = hook_sets[item_name]
        item_type = "Claude Hook Set"
    elif item_name in opencode_plugins:
        config = opencode_plugins[item_name]
        item_type = "OpenCode Plugin"
    else:
        console.print(f"[red]Hook set or plugin '{item_name}' not found.[/red]")
        console.print("Available items:")
        for name in list(hook_sets.keys()) + list(opencode_plugins.keys()):
            console.print(f"  - {name}")
        sys.exit(1)
    
    console.print(f"\n[bold cyan]{item_type}: {item_name}[/bold cyan]")
    console.print(f"[bold]Description:[/bold] {config.get('description', 'No description')}")
    console.print(f"[bold]Version:[/bold] {config.get('version', 'N/A')}")
    console.print(f"[bold]Category:[/bold] {config.get('category', 'general')}")
    
    if item_type == "Claude Hook Set":
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
        console.print(f"  iowarp-hooks install {item_name} claude local{param_str}")
        console.print(f"  iowarp-hooks install {item_name} claude global{param_str}")
    
    else:  # OpenCode Plugin
        environment = config.get("environment", {})
        if environment:
            console.print(f"\n[bold]Environment Variables:[/bold]")
            for env_name, env_value in environment.items():
                console.print(f"  {env_name:20} {env_value}")
        
        files = config.get("files", [])
        if files:
            console.print(f"\n[bold]Files:[/bold]")
            for file_info in files:
                src = file_info.get("src", "")
                dest = file_info.get("dest", "")
                console.print(f"  {src} -> {dest}")
        
        usage = config.get("usage", "")
        if usage:
            console.print(f"\n[bold]Usage:[/bold]")
            console.print(usage)
        
        install_instructions = config.get("install_instructions", "")
        if install_instructions:
            console.print(f"\n[bold]Installation:[/bold]")
            console.print(install_instructions)


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
@click.argument("plugin_name")
@click.option("--global-install", is_flag=True, help="Install plugin globally")
@click.option("--force", is_flag=True, help="Force installation without confirmation")
def install_opencode_plugin(plugin_name: str, global_install: bool, force: bool):
    """Install an OpenCode plugin globally or locally.
    
    This command installs OpenCode plugins by copying them to the OpenCode plugins directory
    and running npm install for dependencies.
    """
    opencode_plugins = get_available_opencode_plugins()
    
    if plugin_name not in opencode_plugins:
        console.print(f"[red]OpenCode plugin '{plugin_name}' not found.[/red]")
        console.print("Available plugins:")
        for name in opencode_plugins.keys():
            console.print(f"  - {name}")
        sys.exit(1)
    
    config = opencode_plugins[plugin_name]
    
    # Determine installation path
    if global_install:
        # Global installation path for OpenCode plugins
        install_path = Path.home() / ".config" / "opencode" / "plugin"
    else:
        # Local installation path
        install_path = Path.cwd() / ".opencode" / "plugin"
    
    if not force:
        console.print(f"\nOpenCode Plugin Installation Summary:")
        console.print(f"  Plugin: {plugin_name}")
        console.print(f"  Description: {config.get('description', 'No description')}")
        console.print(f"  Version: {config.get('version', 'N/A')}")
        console.print(f"  Install Path: {install_path}")
        console.print(f"  Install Type: {'Global' if global_install else 'Local'}")
        
        if not Confirm.ask("Proceed with OpenCode plugin installation?"):
            console.print("Installation cancelled.")
            return
    
    try:
        # Create installation directory
        install_path.mkdir(parents=True, exist_ok=True)
        
        # Get source directory
        source_dir = get_opencode_plugins_directory() / plugin_name
        
        # Copy plugin files directly to plugins directory
        files = config.get("files", [])
        if not files:
            # If no files specified, copy all files (excluding config.yaml and README.md)
            import shutil
            for item in source_dir.iterdir():
                if item.name not in ["config.yaml", "README.md"]:
                    dest_path = install_path / item.name
                    if item.is_file():
                        shutil.copy2(item, dest_path)
                    elif item.is_dir():
                        shutil.copytree(item, dest_path, dirs_exist_ok=True)
        else:
            for file_info in files:
                src_file = source_dir / file_info["src"]
                dest_file = install_path / file_info["dest"]
                
                # Create destination directory if needed
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                import shutil
                shutil.copy2(src_file, dest_file)
                
                # Make executable if needed
                if file_info.get("executable"):
                    os.chmod(dest_file, 0o755)
        
        # Copy environment template if it exists
        env_template = source_dir / ".env.template"
        if env_template.exists():
            import shutil
            shutil.copy2(env_template, install_path / ".env.template")
        
        # Install npm dependencies if package.json exists
        package_json = install_path / "package.json"
        if package_json.exists():
            console.print("Installing npm dependencies...")
            import subprocess
            result = subprocess.run(
                ["npm", "install"], 
                cwd=install_path, 
                capture_output=True, 
                text=True
            )
            if result.returncode != 0:
                console.print(f"[yellow]Warning: npm install failed: {result.stderr}[/yellow]")
            else:
                console.print("[green]npm dependencies installed successfully[/green]")
        
        console.print(f"[green]Successfully installed OpenCode plugin '{plugin_name}'![/green]")
        console.print(f"Plugin installed at: {install_path}")
        
        # Show environment setup instructions
        environment = config.get("environment", {})
        if environment:
            console.print(f"\n[bold yellow]Environment Setup Required:[/bold yellow]")
            console.print("Please set the following environment variables or create a .env file:")
            for env_name, env_value in environment.items():
                console.print(f"  {env_name}={env_value}")
        
        install_instructions = config.get("install_instructions", "")
        if install_instructions:
            console.print(f"\n[bold yellow]Additional Setup:[/bold yellow]")
            console.print(install_instructions)
        
    except Exception as e:
        console.print(f"[red]OpenCode plugin installation failed: {e}[/red]")
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