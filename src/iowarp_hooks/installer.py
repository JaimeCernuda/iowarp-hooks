"""Hook installation logic."""

import json
import shutil
from pathlib import Path
from typing import Dict, Any

from .templates import TemplateProcessor


class HookInstaller:
    """Handles installation of hook sets to target directories."""
    
    def __init__(self, target: str = "claude", install_type: str = "local"):
        self.target = target
        self.install_type = install_type
    
    def get_target_directory(self) -> Path:
        """Get the target directory for hook installation."""
        if self.target == "claude":
            if self.install_type == "global":
                return Path.home() / ".claude"
            else:
                return Path.cwd() / ".claude"
        else:
            raise ValueError(f"Unsupported target: {self.target}")
    
    def install_hook_set(self, hook_set_path: Path, inputs: Dict[str, str], template_processor: TemplateProcessor):
        """Install a hook set to the target directory."""
        target_dir = self.get_target_directory()
        hook_set_name = hook_set_path.name
        
        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create hooks directory
        hooks_dir = target_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        
        # Load hook set configuration
        config_file = hook_set_path / "config.yaml"
        with open(config_file, 'r') as f:
            import yaml
            config = yaml.safe_load(f)
        
        # Track installed files for this hook set
        installed_files = []
        
        # Process and copy hook files
        source_hooks_dir = hook_set_path / "hooks"
        if source_hooks_dir.exists():
            for hook_file in source_hooks_dir.rglob("*"):
                if hook_file.is_file():
                    # Calculate relative path
                    rel_path = hook_file.relative_to(source_hooks_dir)
                    target_file = hooks_dir / rel_path
                    
                    # Track this file
                    installed_files.append(str(target_file.relative_to(target_dir)))
                    
                    # Ensure parent directory exists
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Process template if it's a Python file
                    if hook_file.suffix == ".py":
                        content = template_processor.process_file(hook_file, inputs)
                        with open(target_file, 'w') as f:
                            f.write(content)
                    else:
                        # Copy non-Python files as-is
                        shutil.copy2(hook_file, target_file)
        
        # Update or create settings.json
        self._update_settings(target_dir, config, inputs, hook_set_name, installed_files)
    
    def _update_settings(self, target_dir: Path, config: Dict[str, Any], inputs: Dict[str, str], hook_set_name: str, installed_files: list):
        """Update the settings.json file with hook configurations."""
        settings_file = target_dir / "settings.json"
        
        # Load existing settings or create new
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        # Ensure required sections exist
        if "hooks" not in settings:
            settings["hooks"] = {}
        if "installed_hook_sets" not in settings:
            settings["installed_hook_sets"] = {}
        
        # Process hook configurations from the config
        hook_configs = config.get("hooks", {})
        template_processor = TemplateProcessor()
        
        # Track which hook entries belong to this hook set
        hook_set_entries = {}
        
        for hook_type, hook_config in hook_configs.items():
            # Process templates in hook commands
            processed_config = template_processor.process_data(hook_config, inputs)
            
            # Add metadata to identify this hook set
            processed_config["_hook_set"] = hook_set_name
            
            # Add to settings
            if hook_type not in settings["hooks"]:
                settings["hooks"][hook_type] = []
            
            # Track the index where this hook set's entry will be
            entry_index = len(settings["hooks"][hook_type])
            hook_set_entries[hook_type] = entry_index
            
            # Add the hook configuration
            settings["hooks"][hook_type].append(processed_config)
        
        # Store metadata for this hook set
        settings["installed_hook_sets"][hook_set_name] = {
            "installed_files": installed_files,
            "hook_entries": hook_set_entries,
            "inputs": inputs,
            "config": {
                "name": config.get("name"),
                "version": config.get("version"),
                "description": config.get("description")
            }
        }
        
        # Write updated settings
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    
    def uninstall_hook_set(self, hook_set_name: str):
        """Remove a hook set from the target directory."""
        target_dir = self.get_target_directory()
        settings_file = target_dir / "settings.json"
        
        if not settings_file.exists():
            raise Exception(f"No hooks are installed (settings.json not found)")
        
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        
        # Check if hook set is installed
        installed_hook_sets = settings.get("installed_hook_sets", {})
        if hook_set_name not in installed_hook_sets:
            raise Exception(f"Hook set '{hook_set_name}' is not installed")
        
        hook_set_info = installed_hook_sets[hook_set_name]
        
        # Remove hook files
        for file_path in hook_set_info.get("installed_files", []):
            full_path = target_dir / file_path
            if full_path.exists():
                full_path.unlink()
                print(f"Removed: {file_path}")
        
        # Remove empty directories
        hooks_dir = target_dir / "hooks"
        if hooks_dir.exists():
            # Remove empty subdirectories
            for dir_path in hooks_dir.rglob("*"):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    print(f"Removed empty directory: {dir_path.relative_to(target_dir)}")
        
        # Remove hook entries from settings.json
        hook_entries = hook_set_info.get("hook_entries", {})
        for hook_type, entry_indices in hook_entries.items():
            if hook_type in settings["hooks"]:
                # Remove entries that belong to this hook set (by _hook_set metadata)
                settings["hooks"][hook_type] = [
                    entry for entry in settings["hooks"][hook_type]
                    if entry.get("_hook_set") != hook_set_name
                ]
                
                # Remove empty hook type arrays
                if not settings["hooks"][hook_type]:
                    del settings["hooks"][hook_type]
        
        # Remove hook set metadata
        del installed_hook_sets[hook_set_name]
        
        # Clean up empty sections
        if not settings["hooks"]:
            del settings["hooks"]
        if not installed_hook_sets:
            del settings["installed_hook_sets"]
        
        # Write updated settings or remove file if empty
        if settings:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        else:
            settings_file.unlink()
            print("Removed settings.json (no hooks remaining)")