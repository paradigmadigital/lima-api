# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Lima-API"
copyright = "2025, Paradigma Digital"
author = "Paradigma Digital"
html_short_title = 'lima-api'

#html_logo = 'showcase/insipid.png'
#html_favicon = '_static/favicon.svg'

sys.path.append(os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../../src'))

# -- Get version information from Git -----------------------------------------

try:
    from subprocess import check_output
    import re
    release = check_output(['git', 'describe', '--tags', '--always'])
    release = release.decode().strip()
    release = re.compile("\d+\.\d+.\d+").search(release).group(0)
except Exception:
    release = '<unknown>'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
]
source_suffix = '.md'

# Configuración para autodoc (reemplaza autodoc2)
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Configuración para Napoleon
napoleon_google_docstring = True
napoleon_numpy_docstring = True
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

templates_path = ["_templates"]
exclude_patterns = []

myst_enable_extensions = [
    "amsmath",
    "attrs_inline",
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

# Configurar MyST para que reconozca las directivas de Sphinx (ya incluidas por defecto)
myst_enable_directives = [
    "versionadded",
    "versionchanged", 
    "deprecated",
    "note",
    "warning",
]

# Configurar MyST para procesar docstrings 
myst_dmath_double_inline = True

# Habilitar procesamiento de MyST en docstrings
autodoc_docstring_signature = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_show_sphinx = False

html_sidebars = {
   "**": [
       "globaltoc.html",
       "relations.html",
   ]
}
html_title = f"Lima-API {release} Doc"
html_context = {
    "github_user": "paradigmadigital",
    "github_repo": "lima-api",
    "github_version": "main",
    "doc_path": "docs/source",
}

html_theme_options = {
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["search-field"],
    "navbar_end": ["navbar-icon-links"],
    "navbar_persistent": [],
    "navbar_align": "content",
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/paradigmadigital/lima-api/",
            "icon": "fab fa-github",
            "type": "fontawesome",
        },
        {
            "name": "X",
            "url": "https://x.com/paradigmate",
            "icon": "fa-brands fa-x-twitter",
        },
        {
            "name": "YouTube",
            "url": "https://www.youtube.com/c/ParadigmaDigital",
            "icon": "fab fa-youtube",
        },
   ]
}
