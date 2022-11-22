#!/usr/bin/env python3

## command line interface to run {{ cookiecutter.pipeline_name }} pipeline and helper functions


import os, sys, time, shutil, argparse, json, yaml, re, textwrap
import pandas as pd
from pathlib import Path

import logzero
from logzero import logger as log
logzero.loglevel(logzero.INFO)

from cookiecutter.main import cookiecutter

SCRIPT_DIR = Path(sys.path[0])

CLUSTER_LOCAL = """snakemake --snakefile {sdir}/Snakefile --cores 1 --use-conda --conda-prefix /nfs/team205/jp30/conda_envs/snakemake""".format(sdir = str(SCRIPT_DIR))

CLUSTER_GLOBAL = """snakemake --snakefile {sdir}/Snakefile  --use-conda --conda-prefix /nfs/team205/jp30/conda_envs/snakemake --cluster '{sdir}/lsf_submit.sh -q {{ '{{' }}cluster.q{{ '}}' }} -e {{ '{{' }}cluster.e{{ '}}' }} -o {{ '{{' }}cluster.o{{ '}}' }} -n {{ '{{' }}cluster.n{{ '}}' }} -M {{ '{{' }}cluster.M{{ '}}' }} -R"select[mem>{{ '{{' }}cluster.M{{ '}}' }}] rusage[mem={{ '{{' }}cluster.M{{ '}}' }}] span[hosts=1]"' --cluster-cancel '{sdir}/lsf_cancel.sh' --cluster-status '{sdir}/lsf_status.sh' --cluster-config {sdir}/cluster_config.yaml --jobs 100 --latency-wait 180 --restart-times 3""".format(
    sdir = str(SCRIPT_DIR)
)

############################## HELPER FUNCTIONS

def setup_working_directory(args):
    """
    setup a working directory for running the pipeline
    """
    
    # create working directory
    working_dir = Path(time.strftime(args.dirname))
    try:
        (working_dir / "dataset_configs").mkdir(parents=True)
        log.info("working directory {} created...".format(str(working_dir)))
    except FileExistsError:
        log.warning("directory {} already exists!".format(str(working_dir)))
        if input("overwrite? [yes/NO] ") == "yes":
            log.warning("directory exists: overwriting!")
            shutil.rmtree(str(working_dir))
            (working_dir / "dataset_configs").mkdir(parents=True)
        else:
            log.error("directory exists: quitting!")
            return 1

    # symlink to wrapper or add alias to bashrc
    (working_dir / "cellregulon").symlink_to(SCRIPT_DIR / "cellregulon.py")

    log.info("all done.")

        
def cleanup_cluster_log(args):
    """
    delete log files created during cluster execution
    """
    log.warning("cleaning cluster log...")
    def rmdir(dir_name):
        dir_path = Path(dir_name)
        if dir_path.is_dir():
            for item in dir_path.iterdir():
                if item.is_dir():
                    rmdir(item)
                else:
                    item.unlink()
            dir_path.rmdir()

    rmdir("cluster_log")
    log.info("all done.")


############################## RUN PIPELINES

def run_pipeline(args):
    """
    run a pipeline locally or on cluster
    """
    # dry run
    if args.mode in ["dryrun", "d"]:
        log.info("dry run...")
        command = CLUSTER_LOCAL + " " + "-nr"
        if args.snake_options:
            command += " " + " ".join(args.snake_options)
        command += " | less -SR"

    # local command
    if args.mode in ["local", "l"]:
        log.info("running locally...")
        command = CLUSTER_LOCAL
        if args.snake_options:
            command += " " + " ".join(args.snake_options)

    # cluster command
    elif args.mode in ["cluster", "c"]:
        log.info("running on cluster...")
        command  = CLUSTER_GLOBAL
        if args.snake_options:
            command += " " + " ".join(args.snake_options)
        command = "set -e; " + command

    # run
    log.info(command)
    os.system(command)
    log.info("all done.")


############################## DEFINE PARSER

parser = argparse.ArgumentParser(description="run {{ cookiecutter.pipeline_name }} pipeline and helpers")
subparsers = parser.add_subparsers(title="subcommands",   metavar="COMMAND", help='use COMMAND -h for more information')

### HELPERS

#--- parser for setup_working_directory
parser_working_dir = subparsers.add_parser('working_dir', help="setup a working directory for running the pipeline")
parser_working_dir.add_argument('--dirname', '-d',   default="results_%Y_%m_%d/", help="name of directory")
parser_working_dir.set_defaults(func=setup_working_directory)


### PIPELINES

#--- parser for running pipeline
parser_mapping = subparsers.add_parser('run', help="run pipeline")
parser_mapping.add_argument('mode', choices=["local","l","cluster","c","dryrun","d"], help="run locally or on cluster?")
parser_mapping.add_argument('snake_options', nargs=argparse.REMAINDER, help="pass options to snakemake (...)")
parser_mapping.set_defaults(func=run_pipeline)

#--- parser for cleanup_cluster_log
parser_cleanup_log = subparsers.add_parser('cleanup_log', help="delete log files from cluster execution")
parser_cleanup_log.set_defaults(func=cleanup_cluster_log)


############################## PARSE ARGUMENTS

if len(sys.argv)==1:
    parser.print_help()
    sys.exit(1)
args = parser.parse_args()
#print(args)

############################## EXECUTE CHOSEN FUNCTION

args.func(args)



