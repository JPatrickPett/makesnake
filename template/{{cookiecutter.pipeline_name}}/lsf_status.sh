#!/bin/bash

# used by snakemake to get job status
# get jobstatus with bjobs command and convert to expected categories:
# ['running', 'success', 'failed']

jobid="$1"
job_status=$(bjobs -w "$jobid" | tr -s ' ' | cut -f3 -d' ' | tail -n +2)


job_status_out=""

case "$job_status" in
	EXIT)
		job_status_out="failed"
		;;
	PSUSP)
		job_status_out="failed"
		;;
	USUSP)
		job_status_out="failed"
		;;
	SSUSP)
		job_status_out="failed"
		;;
	RUN)
		job_status_out="running"
		;;
	PEND)
		job_status_out="running"
		;;
	UNKWN)
		job_status_out="running"
		;;
	DONE)
		job_status_out="success"
		;;
	*)
		job_status_out="failed"
		;;
esac


echo "$job_status_out"
