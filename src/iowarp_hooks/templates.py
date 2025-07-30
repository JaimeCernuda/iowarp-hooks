"""Template processing for hook files."""

import re
from pathlib import Path
from typing import Dict, Any, Union

from jinja2 import Template


class TemplateProcessor:
    """Processes template files and data structures with variable substitution."""
    
    def process_file(self, file_path: Path, variables: Dict[str, str]) -> str:
        """Process a template file with variable substitution."""
        with open(file_path, 'r') as f:
            content = f.read()
        
        return self.process_string(content, variables)
    
    def process_string(self, content: str, variables: Dict[str, str]) -> str:
        """Process a string with variable substitution using Jinja2."""
        # First, handle simple {variable} style replacements for backwards compatibility
        for key, value in variables.items():
            content = content.replace(f"{{{key}}}", str(value))
        
        # Then use Jinja2 for more advanced templating
        template = Template(content)
        return template.render(**variables)
    
    def process_data(self, data: Any, variables: Dict[str, str]) -> Any:
        """Recursively process data structures with variable substitution."""
        if isinstance(data, str):
            return self.process_string(data, variables)
        elif isinstance(data, dict):
            return {key: self.process_data(value, variables) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.process_data(item, variables) for item in data]
        else:
            return data