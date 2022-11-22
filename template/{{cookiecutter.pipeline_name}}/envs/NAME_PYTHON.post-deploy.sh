#!/bin/bash

conda activate $CONDA_PREFIX

python -m ipykernel install --user --name=NAME
