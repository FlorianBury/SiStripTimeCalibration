conda env create -n timing --file ENV.yml
export SETUPTOOLS_ENABLE_FEATURES=legacy-editable
pip install -e .
