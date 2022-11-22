#!/bin/bash

# used by snakemake to cancel jobs

jobid="$1"

bkill "$jobid"
