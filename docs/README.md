# Updating the Documentation
Make sure to install `Sphinx` and `sphinx_rtd_theme` with pip if you're 
building locally. Otherwise, just `Sphinx` should be enough.

When updating the docs, it should be sufficient to delete /docs/sources and 
then run (from the project root):
```bash
sphinx-apidoc -o ./docs/sources rach3datautils
```
If you want to build the page, cd into /docs and run:
```bash
make html
```
