#!/usr/bin/env python3

## command line interface to run {{ cookiecutter.pipeline_name }} pipeline and helper functions


import os
import sys
import time
import shutil
import argparse
import textwrap

from pathlib import Path
import pandas as pd
import logzero
from logzero import logger as log
logzero.loglevel(logzero.INFO)

from cookiecutter.main import cookiecutter

SCRIPT_DIR = Path(sys.path[0])

CLUSTER_LOCAL = """snakemake --snakefile {sdir}/Snakefile --cores 1 --use-conda --conda-prefix /nfs/team205/jp30/conda_envs/snakemake""".format(sdir = str(SCRIPT_DIR))

CLUSTER_GLOBAL = """snakemake --snakefile {sdir}/Snakefile  --use-conda --conda-prefix /nfs/team205/jp30/conda_envs/snakemake --cluster '{sdir}/lsf_submit.sh -q {{ '{{' }}cluster.q{{ '}}' }} -e {{ '{{' }}cluster.e{{ '}}' }} -o {{ '{{' }}cluster.o{{ '}}' }} -n {{ '{{' }}cluster.n{{ '}}' }} -M {{ '{{' }}cluster.M{{ '}}' }} -R"select[mem>{{ '{{' }}cluster.M{{ '}}' }}] rusage[mem={{ '{{' }}cluster.M{{ '}}' }}] span[hosts=1]"' --cluster-cancel '{sdir}/lsf_cancel.sh' --cluster-status '{sdir}/lsf_status.sh' --cluster-config cluster_config.yaml --jobs 100 --latency-wait 180 --restart-times 3""".format(
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
        working_dir.mkdir(parents=True)
        log.info("working directory {} created...".format(str(working_dir)))
    except FileExistsError:
        log.warning("directory {} already exists!".format(str(working_dir)))
        if input("overwrite? [yes/NO] ") == "yes":
            log.warning("directory exists: overwriting!")
            shutil.rmtree(str(working_dir))
            working_dir.mkdir(parents=True)
        else:
            log.error("directory exists: quitting!")
            return 1

    # copy config file
    shutil.copy(SCRIPT_DIR / "config.yaml", working_dir / "config.yaml")
    shutil.copy(SCRIPT_DIR / "cluster_config.yaml", working_dir / "cluster_config.yaml")

    # symlink to wrapper or add alias to bashrc
    (working_dir / "{{ cookiecutter.pipeline_name }}").symlink_to(SCRIPT_DIR / "{{ cookiecutter.pipeline_name }}.py")

    log.info("all done.")


def open_cluster_log(args):
    """
    open log file from cluster execution
    """
    log.info("select rule to show cluster log for...")
    
    cluster_log_dir = Path("cluster_log")
    log_files = list(cluster_log_dir.glob("*"))
    search_pattern = "(?P<rule>[^.]+).(?P<id>[^.]+).(?P<type>[^.]+)"

    file_df = pd.DataFrame(dict(mtime=[p.stat().st_mtime for p in log_files], filename=[p.name for p in log_files]))
    extr_df = file_df.filename.str.extract(search_pattern, expand=True)
    file_df = file_df.join(extr_df)
    file_df = file_df.sort_values("mtime", ascending=False)

    log.debug(file_df)

    opt = dict(enumerate(file_df.rule.unique().tolist()))
    print("\n".join(f"[{i}] {r}" for i, r in opt.items()))
    choice = input("\nselect [0]: ") or 0

    query_pattern = f"rule == '{opt[int(choice)]}' and type == '{str(args.kind)}'"
    file_sel = file_df.query(query_pattern)["filename"].tolist()[0]
    path_sel = cluster_log_dir / file_sel

    log.info(f"open {path_sel}")

    os.system(f"less -R {path_sel}")

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

def _add_cmd_options(cmd, args):
    command = cmd
    if args.snake_options:
        command += " " + " ".join(args.snake_options)
    return command


def run_pipeline(args):
    """
    run a pipeline locally or on cluster
    """
    # dry run
    if args.mode in ["dryrun", "d"]:
        log.info("dry run...")
        command = CLUSTER_LOCAL + " " + "-nr"
        command = _add_cmd_options(command, args)
        command += " | less -SR"

    # local command
    if args.mode in ["local", "l"]:
        log.info("running locally...")
        command = CLUSTER_LOCAL
        command = _add_cmd_options(command, args)

    # cluster command
    elif args.mode in ["cluster", "c"]:
        log.info("running on cluster...")
        command = CLUSTER_GLOBAL
        command = _add_cmd_options(command, args)
        command = "set -e; " + command
        Path("cluster_log").mkdir(exist_ok=True)

    # run
    log.info(command)
    os.system(command)

    # execute after dryrun
    if args.mode in ["dryrun", "d"]:
        run_for_real = input("run: [l]ocal - [c]luster - [E]xit ... ")
        if run_for_real == "l":
            args.mode = "local"
            run_pipeline(args)
        elif run_for_real == "c":
            args.mode = "cluster"
            run_pipeline(args)

    log.info("all done.")


############################## DEFINE PARSER

parser = argparse.ArgumentParser(description="run {{ cookiecutter.pipeline_name }} pipeline and helpers")
subparsers = parser.add_subparsers(title="subcommands",   metavar="COMMAND", help='use COMMAND -h for more information')

### HELPERS

#--- parser for setup_working_directory
parser_working_dir = subparsers.add_parser('working_dir', help="setup a working directory for running the pipeline")
parser_working_dir.add_argument('--dirname', '-d',   default="results_%Y_%m_%d/", help="name of directory")
parser_working_dir.set_defaults(func=setup_working_directory)

#--- parser for open_cluster_log
parser_working_dir = subparsers.add_parser('open_cluster_log', help="open log file created by cluster execution (opens newest log file)")
parser_working_dir.add_argument('--kind', '-k', choices=["out", "err"],  default="err", help="which kind of log file to open")
parser_working_dir.set_defaults(func=open_cluster_log)

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



