# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
import django

sys.path.append(os.path.abspath('../..'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'App.settings'

django.setup()

sys.path.append(os.path.abspath('../../CinnamonSwirl'))

project = 'CinnamonSwirl Backend'
copyright = '2022, Marenzers, LazyDuckling'
author = 'Marenzers, LazyDuckling'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc']

rst_prolog = """
.. |login| replace:: **Requires login** 
.. |requires| replace:: **Required arguments:** 
.. |contains| replace:: **Response contains:**
.. |redirect| replace:: **Redirects to:**
"""

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
