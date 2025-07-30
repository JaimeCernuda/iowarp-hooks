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
        
        # Process and copy hook files
        source_hooks_dir = hook_set_path / "hooks"
        if source_hooks_dir.exists():
            for hook_file in source_hooks_dir.rglob("*"):
                if hook_file.is_file():
                    # Calculate relative path
                    rel_path = hook_file.relative_to(source_hooks_dir)
                    target_file = hooks_dir / rel_path
                    
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
        self._update_settings(target_dir, config, inputs)
    
    def _update_settings(self, target_dir: Path, config: Dict[str, Any], inputs: Dict[str, str]):
        """Update the settings.json file with hook configurations."""
        settings_file = target_dir / "settings.json"
        
        # Load existing settings or create new
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        # Ensure hooks section exists
        if "hooks" not in settings:
            settings["hooks"] = {}
        
        # Process hook configurations from the config
        hook_configs = config.get("hooks", {})
        template_processor = TemplateProcessor()
        
        for hook_type, hook_config in hook_configs.items():
            # Process templates in hook commands
            processed_config = template_processor.process_data(hook_config, inputs)
            
            # Add to settings
            if hook_type not in settings["hooks"]:
                settings["hooks"][hook_type] = []
            
            # Add the hook configuration
            settings["hooks"][hook_type].append(processed_config)
        
        # Write updated settings
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    
    def uninstall_hook_set(self, hook_set_name: str):
        """Remove a hook set from the target directory."""
        target_dir = self.get_target_directory()
        
        # Remove hook files (this is basic - could be improved with metadata tracking)
        hooks_dir = target_dir / "hooks"
        if hooks_dir.exists():
            # For now, we'll just warn the user
            print(f"Note: Hook files in {hooks_dir} should be manually removed.")
            print("Future versions will track installed files for automatic removal.")
        
        # Remove from settings.json would require tracking which hooks belong to which set
        print("Note: settings.json entries should be manually removed.")
        print("Future versions will track hook set origins for automatic removal.")