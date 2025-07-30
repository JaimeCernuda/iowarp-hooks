#!/usr/bin/env python3
"""Migrate existing settings.json to separate metadata file."""

import json
from pathlib import Path

def migrate_settings():
    """Migrate Claude Code settings to use separate metadata file."""
    settings_file = Path(".claude/settings.json")
    metadata_file = Path(".claude/.hook_metadata.json")
    
    if not settings_file.exists():
        print("No settings.json found to migrate")
        return
    
    # Load current settings
    with open(settings_file, 'r') as f:
        settings = json.load(f)
    
    # Extract metadata
    metadata = {}
    if "installed_hook_sets" in settings:
        metadata["installed_hook_sets"] = settings.pop("installed_hook_sets")
    
    # Remove _hook_set fields from hooks
    if "hooks" in settings:
        for hook_type, hook_list in settings["hooks"].items():
            for hook in hook_list:
                if "_hook_set" in hook:
                    hook.pop("_hook_set")
    
    # Write clean settings
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    # Write metadata if any
    if metadata:
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"✅ Migrated metadata to {metadata_file}")
    
    print(f"✅ Cleaned {settings_file} for Claude Code compatibility")

if __name__ == "__main__":
    migrate_settings()