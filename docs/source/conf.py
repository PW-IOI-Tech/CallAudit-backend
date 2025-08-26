# Configuration file for the Sphinx documentation builder.
import os
import sys
from datetime import datetime  # For dynamic copyright year

# -- Project information -----------------------------------------------------
project = "QC-Call-Audit-Backend"
copyright = "2025, Shoyeb Ansari"
author = "Shoyeb Ansari"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
# Add the path to your project's source code so Sphinx can find the modules
# This assumes your code is in src/ at the project root
sys.path.insert(0, os.path.abspath("../../src"))

extensions = [
    "sphinx.ext.autodoc",  # Core autodoc functionality
    "sphinx.ext.viewcode",  # Add source code links
    "sphinx.ext.napoleon",  # Support for Google/NumPy style docstrings
    "sphinx.ext.autosummary",  # Generate summary tables
    "sphinx_autodoc_typehints",  # Better rendering of type hints
]

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"  # A popular, clean theme
html_static_path = ["_static"]

# -- Options for sphinx.ext.autodoc -----------------------------------------
# Configure autodoc to be as comprehensive as possible
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
    "show-inheritance": True,
}

# -- Options for sphinx.ext.napoleon (Google/NumPy style) --------------------
# Your docstrings look like Google style, so enable that
napoleon_google_docstring = True
napoleon_numpy_docstring = False  # Disable if you're only using Google style
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# -- Options for sphinx_autodoc_typehints ------------------------------------
# Make type hints look nice
set_type_checking_flag = False
typehints_fully_qualified = False
always_document_param_types = False
typehints_document_rtype = True
