# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import tomllib
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
with open(REPO_ROOT / "pyproject.toml", "rb") as fh:
    pyproject = tomllib.load(fh)

project = pyproject["project"]["name"]
author = pyproject["project"]["authors"][0]["name"]
copyright = f"{date.today().year}, {author}"
release = pyproject["project"]["version"]

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "shibuya"
html_theme_options = {
    "accent_color": "indigo",
    "nav_links_align": "right",
    "show_ai_links": False,
    "github_url": "https://github.com/loic-simon/comdab",
}
html_context = {
    "source_type": "github",
    "source_user": "loic-simon",
    "source_repo": "comdab",
}


# -- Extensions options ------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/stable/", None),
}
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "member-order": "bysource",
    "exclude-members": "__init__,Path,model_config",
    "no-index-entry": True,
}
autodoc_class_signature = "separated"
