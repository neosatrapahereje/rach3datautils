# Building the Documentation
When building make sure to install the package itself with all it's 
requirements, plus the requirements.txt from this directory.

To build the docs, first run the following command from the project 
root:
```bash
sphinx-apidoc -o ./docs/sources rach3datautils
```
Then to build a html version of the docs run the following from the docs 
directory.
```bash
make html
```
