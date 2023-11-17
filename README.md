# rach3datautils

This Python package contains tools for managing the Rach3 dataset.

## Development

### Creating an Environment

<details>
<summary>with Python and Pip</summary>

Make sure you're running Python 3.9 or above. Clone the repo, and then do the 
following from the project root:

 - Create the virtual env
```shell
python -m venv venv
```
 - Activate the virtual env. This differs between shells, see 
[here](https://docs.python.org/3/library/venv.html#how-venvs-work)
 - Install packages from requirements.txt:
```shell
pip install -r requirements.txt
```
 - Install rach3datautils with extras in develop mode:
```shell
pip install -e .[EXTRA]
```
</details>
<details>
<summary>with Conda</summary>

Clone the repo and then do the following from the project root:

 - Create a Conda environment using the environment.yml file:
```shell
conda env create -f environment.yml
```
 - Activate the environment:
```shell
conda activate rach3datautils
```
</details>

### Log Level
The log level of the package can be set as an environment variable.

To use a .env file, put ```RACH3DATAUTILS_LOGLEVEL=LOGLEVEL``` in a .env file 
in the project root.

Possible log levels include: "DEBUG", "INFO", "WARNING", "ERROR",  and 
"CRITICAL".

