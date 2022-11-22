#!/bin/bash

# used by snakemake to submit jobs
# extract only the jobid from bsub output, which is a sentence like
# 'job with jobid <12345> submitted to queue <normal>.'

jobid=$(bsub "$@" | grep -Po "(?<=<)([0-9]+)(?=>)")

echo $jobid
