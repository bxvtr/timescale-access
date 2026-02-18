"""Configuration file for the Sphinx documentation builder."""

from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

# Add the project root (one level up from docs/) to sys.path
sys.path.insert(0, os.path.abspath("../.."))
# Add the src directory explicitly so that `timescale_access` can be imported
sys.path.insert(0, os.path.abspath("../../src"))

# ---------------------------------------------------------------------------
# Project information
# ---------------------------------------------------------------------------

project = "Timescale Access"
author = "bxvtr"
copyright = "2026, bxvtr"  # noqa: A003
release = "0.1.0"

# ---------------------------------------------------------------------------
# General configuration
# ---------------------------------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",        # Pull in docstrings from your code
    "sphinx.ext.autosummary",    # Generate summary pages automatically
    "sphinx.ext.napoleon",       # Support for Google/NumPy style docstrings
    "sphinx.ext.viewcode",       # Add links to highlighted source code
    "sphinx_autodoc_typehints",  # Render type hints nicely in the docs
    "sphinx_rtd_dark_mode",      # Dark mode support for Read the Docs theme
]

autosummary_generate = True      # Turn on autosummary
autodoc_typehints = "description"

templates_path = ["_templates"]
exclude_patterns: list[str] = []

# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# ---------------------------------------------------------------------------
# Autodoc options
# ---------------------------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

autodoc_typehints = "description"
