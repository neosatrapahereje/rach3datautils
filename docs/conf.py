# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

sys.path.insert(0, os.path.abspath(".."))


project = 'rach3datautils'
copyright = '2023, Carlos Cancino-Chacón, Uros Zivanovic'
author = 'Carlos Cancino-Chacón, Uros Zivanovic'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon",
              "sphinx.ext.intersphinx"]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Options for Intersphinx -------------------------------------------------
intersphinx_mapping = {
    "partitura": ("https://partitura.readthedocs.io/en/latest/", None),
    "numpy": ('https://numpy.org/doc/stable/', None),
    "python": ('https://docs.python.org/3/', None),
    "madmom": ('https://madmom.readthedocs.io/en/latest/', None)
}
intersphinx_disabled_reftypes = ["std:*", "cpp:*"]
