# Sphinx configuration file for SPARQL Agent API documentation

import os
import sys
from datetime import datetime

# Add source directory to path
sys.path.insert(0, os.path.abspath('../src'))

# Project information
project = 'SPARQL Agent'
copyright = f'{datetime.now().year}, David'
author = 'David'
release = '0.1.0'
version = '0.1'

# General configuration
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.githubpages',
    'sphinx_autodoc_typehints',
    'myst_parser',
]

# Source file suffixes
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# Master document
master_doc = 'index'

# Language
language = 'en'

# Exclude patterns
exclude_patterns = ['_build', 'Thumb.db', '.DS_Store']

# Pygments style
pygments_style = 'sphinx'

# HTML output options
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
}

html_static_path = ['_static']
html_css_files = ['custom.css']

# HTML context
html_context = {
    'display_github': True,
    'github_user': 'david4096',
    'github_repo': 'sparql-agent',
    'github_version': 'main',
    'conf_py_path': '/docs/',
}

# Autodoc configuration
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'

# Napoleon settings (Google-style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Intersphinx configuration
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'requests': ('https://requests.readthedocs.io/en/latest/', None),
    'rdflib': ('https://rdflib.readthedocs.io/en/stable/', None),
}

# MyST Parser configuration
myst_enable_extensions = [
    'colon_fence',
    'deflist',
    'fieldlist',
    'html_admonition',
    'html_image',
    'linkify',
    'replacements',
    'smartquotes',
    'strikethrough',
    'substitution',
    'tasklist',
]

# Todo extension
todo_include_todos = True

# Coverage
coverage_show_missing_items = True
