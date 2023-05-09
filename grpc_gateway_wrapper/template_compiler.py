"""
A minimal replacement for pybars with no license issues
"""

# Standard
from typing import Dict
import re


class TemplateCompiler:
    """minimal replacement for pybars compiler without license issues"""

    def __init__(self, template_content: str):
        self.template_content = template_content

    def __call__(self, template_dict: Dict[str, str]) -> str:
        for template_key, template_val in template_dict.items():
            self.template_content = re.sub(
                r"{{\s*" + template_key + r"\s*}}", template_val, self.template_content
            )
        return self.template_content
