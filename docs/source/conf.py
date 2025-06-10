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

# -- Get version information from Git -----------------------------------------

try:
    from subprocess import check_output
    release = check_output(['git', 'describe', '--tags', '--always'])
    release = release.decode().strip()
except Exception:
    release = '<unknown>'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx_design",
    "autodoc2",
]
source_suffix = '.md'
autoapi_dirs = [
    '../../src',
    '../../'
]
autodoc2_packages = [
    {
        "path": "../../src/lima_api",
        "auto_mode": True,
    },
]
autodoc2_docstring_parser_regexes = [
    (r".*", "myst"),
]

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
html_theme_options = {
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
