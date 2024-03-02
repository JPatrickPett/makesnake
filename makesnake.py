#!/usr/bin/env python3

## run makesnake

__version__ = "0.6"

import os, sys, time, shutil, argparse, json, yaml, re, textwrap, codecs
import tempfile
import pandas as pd
from pathlib import Path

import logzero
from logzero import logger as log
logzero.loglevel(logzero.INFO)

from cookiecutter.main import cookiecutter

SCRIPT_DIR = Path(sys.path[0])

file_path_pattern = "(?P<path>.*?)(?P<filename>[^/.]+)(?P<extension>[^/]*)$"
keyword_comment_pattern = "[^#]*# *(?P<keyword>input|output|params|log|threads) +(?P<name>\S+): +<(?P<value>[^<>]+)>"

############################## RUN

def make_pipeline(args):
    """
    create pipeline from list of scripts
    """
    log.info("starting pipeline creation")
    log.info("gathering context")
    context = {}

    # 1) get fixed params
    context["makesnake_version"] = __version__

    # 2) ask for additional params
    context["pipeline_name"] = input("pipeline_name: ")

    # 3) parse list of scripts
    context["context"] = {"rules": []}
    log.info(f"parsing info from script files, context so far: {context}")
    for f in args.script:
        m_file = re.match(file_path_pattern, f.name)

        script_rule = {
            "name": m_file.group("filename"),
            "keywords": {},
        }

        log.info(f"parsing file {script_rule['name']}, path: {f.name}")
        for line in f.readlines():
            # extract keywords from comments
            m = re.match(keyword_comment_pattern, line)
            if m:
                kw, name, val = m.group("keyword"), m.group("name"), m.group("value")
                val = codecs.decode(val, 'unicode_escape')
                if kw in ["input"]:
                    m = re.match(file_path_pattern, val.strip('\'"'))
                    val = f"\"{m.group('path')}{m.group('filename')}_{{runID}}{m.group('extension')}\""
                elif kw in ["output", "log"]:
                    m = re.match(file_path_pattern, val.strip('\'"'))
                    val = f"RESULTDIR / \"{m.group('path')}{m.group('filename')}_{{runID}}{m.group('extension')}\""

                if kw in ["threads"]:
                    script_rule["keywords"][kw] = val
                elif not kw in script_rule["keywords"]:
                    script_rule["keywords"][kw] = {name: val}
                else:
                    script_rule["keywords"][kw][name] = val

        # add extra keywords
        script_rule["keywords"]["conda"] = f"envs/{script_rule['name']}.yaml"

        extension = m_file.group("extension")
        run_method = {
            ".py": dict(kw="script", val="{{SCRIPTDIR}}/{script_path}"),
            ".R": dict(kw="script", val="{{SCRIPTDIR}}/{script_path}"),
            ".ipynb": dict(kw="notebook", val="{{SCRIPTDIR}}/{script_path}"),
            ".sh": dict(kw="shell", val="{{SCRIPTDIR}}/{script_path} {{input:q}} {{output:q}} {{params:q}}"),
        }
        script_rule["keywords"][run_method[extension]["kw"]] = run_method[extension]["val"].format(script_path = str(Path(f.name).name))

        if extension == ".ipynb":
            notebook_path = f"NOTEBOOKDIR / \"notebook_{script_rule['name']}_{{runID}}.ipynb\""
            if "log" not in script_rule["keywords"]:
                script_rule["keywords"]["log"] = {"notebook": notebook_path}
            else:
                script_rule["keywords"]["log"]["notebook"] = notebook_path

        log.info(f"context for script: {script_rule}")
        context["context"]["rules"].append(script_rule)

    # fix rule names (snakemake does not allow leading digits)
    try:
        # try stripping leading digits
        strip_regex = "^[0-9_]+"
        rule_names = [re.sub(strip_regex, "", rule["name"]) for rule in context["context"]["rules"]]
        assert len(rule_names)==len(set(rule_names)), "rule names have to remain unique"
        for rule in context["context"]["rules"]:
            rule["name"] = re.sub(strip_regex, "", rule["name"])
    except AssertionError:
        # add leading 'num' to rules starting with a digit
        for rule in context["context"]["rules"]:
            if re.match(rule["name"], "[0-9].*"):
                rule["name"] = "num" + rule["name"]

    log.info(f"context: {context}")

    # 4) create environment and post_deploy scripts (skip for now)
    # 5) run cookiecutter
    with tempfile.TemporaryDirectory() as dirpath:
        template_dir = Path(dirpath) / "template"

        log.info(f"copy template to tmp dir: {template_dir}")
        shutil.copytree(
            f"{SCRIPT_DIR}/template",
            template_dir
        )

#        run_tmpl = Path(template_dir) / "{{cookiecutter.project_id}}" / "envs" / "NAME.yaml"
#        log.info(f"expand template: {run_tmpl}")
#        for rule in context["rules"]:
#            new_file = Path(str(run_tmpl).replace("NAME", rule["name"]))
#
#            log.info(f"...save as {new_file}")
#            shutil.copy(
#                str(run_tmpl),
#                str(new_file),
#            )   
#            content = Path(new_file).read_text()
#            content = content.replace("NAME", grp)
#            new_file.write_text(content)
#            run_tmpl.unlink()

        log.info("run cookiecutter")
        cookiecutter(
            str(template_dir),
            output_dir = "",
            extra_context = context,
            overwrite_if_exists = True,
            no_input = True,
        )

    # move script file into new folder
    log.info("move script files into new folder")
    for f in args.script:
        shutil.copy(
            f.name,
            f"{context['pipeline_name']}/scripts/"
        )

    log.info("all done.")


############################## DEFINE PARSER

parser = argparse.ArgumentParser(description="run makesnake: create snakemake pipeline from list of scripts")

parser.add_argument('script', action = "extend", nargs = "+", type = argparse.FileType('r'), help = "list of scripts")
parser.set_defaults(func=make_pipeline)


############################## PARSE ARGUMENTS

if len(sys.argv)==1:
    parser.print_help()
    sys.exit(1)
args = parser.parse_args()
#print(args)

############################## EXECUTE CHOSEN FUNCTION

args.func(args)



