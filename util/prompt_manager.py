"""Prompt management using Jinja2 templates."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader



class PromptManager:
    """Manager for loading and rendering Jinja2 prompt templates."""

    def __init__(self, templates_dir: str = "util/prompts"):
        """Initialize prompt manager.

        Args:
            templates_dir: Directory containing Jinja2 templates
        """
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Render a template with given context.

        Args:
            template_name: Name of template file (e.g., 'harmonization.j2')
            **kwargs: Template variables

        Returns:
            Rendered template string
        """
        try:
            template = self.env.get_template(template_name)
            rendered: str = template.render(**kwargs)
            return rendered
        except Exception as e:
            raise

    def render_string(self, template_string: str, **kwargs: Any) -> str:
        """Render a template from string.

        Args:
            template_string: Template string
            **kwargs: Template variables

        Returns:
            Rendered template string
        """
        try:
            template = self.env.from_string(template_string)
            rendered: str = template.render(**kwargs)
            return rendered
        except Exception as e:
            raise


# Global prompt manager instance
prompt_manager = PromptManager()
