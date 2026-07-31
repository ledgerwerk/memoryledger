from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

project = "memoryledger"
author = "Memoryledger contributors"

try:
    from memoryledger import __version__
except Exception:
    __version__ = "0.0.0"

version = __version__
release = __version__

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]

source_suffix = {".md": "markdown"}
master_doc = "index"
exclude_patterns = ["_build", "README.md", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path: list[str] = []
templates_path: list[str] = []

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 3
autosectionlabel_prefix_document = True
# The site uses explicit MyST autodoc directives; leaving autosummary disabled
# avoids implicit generated RST pages in the Markdown-only source tree.
autosummary_generate = False

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "show-inheritance": True,
}
autodoc_typehints = "description"
always_document_param_types = True

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True

nitpicky = True
