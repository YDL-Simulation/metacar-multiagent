from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

project = "metacar-multiagent"
copyright = "2026, YDL-Simulation"
author = "YDL-Simulation"
release = "0.1.0"

extensions = ["sphinx.ext.autodoc", "sphinxcontrib.autodoc_pydantic"]
autodoc_pydantic_model_show_json = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_field_show_alias = False
templates_path = []
exclude_patterns = ["_build"]
language = "zh_CN"
html_theme = "sphinx_rtd_theme"
