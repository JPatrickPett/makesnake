# makesnake

Template and CLI to automatically generate a snakemake pipeline from list of scripts.

Usage:

```bash
makesnake.py script1.py script2.R script3.sh notebook4.ipynb
```

This creates a new folder in the working directory with a snakemake pipeline, including `Snakefile`, scripts copied into a `scripts/` folder, `config.yaml` file with the parameter values, `cluster_config.yaml` to define default resources, an empty `envs/` folder to be filled with environment specifications and a command line interface to run the pipeline.

Supported scripts are:
- python (.py)
- R (.R)
- shell (.sh)
- jupyter notebook (.ipynb)

*note:* some generated files may need to be adjusted. Cluster configurations are specific for an LSF cluster, but can be adjusted at the beginning of the CLI file.

## preparing scripts

Snakemake determines the order in which pipeline steps are executed based on input and output files. Therefore the pipeline structure does not have to be defined manually. However, scripts need to be annotated with comments defining inputs and outputs, which will pe parsed by `makesnake`.

So, in order to work, add comments like this to each script:

```python
# input in_path: </path/to/infile.txt>
# input prev_rule_done: <done/previous_rule.done>
# output out_path: </path/to/outfile.txt>
# params number: <123>
# params string: <text>
# params a_list: <["a", "b", "c"]>
```

The contents in `<...>` will end up in the `config.yaml` file as default parameters.
The `input` and `output` comments will translate into snakemake input and output definitions. To make the script run, only after another script has finished, even when the other script does not create any output files use `# input STEP_done: <done/STEP.done>` as input and output (it creates an empty dummy file to indicate snakemake the step has finished).
Note, relative paths will be within the results folder created when running the pipeline. They should be used for most intermediate results.

Depending on the file type, corresponding [snakemake keywords](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#external-scripts) are used. For example, an `.ipynb` file will be executed using snakemakes `notebook:` keyword, for `.py` and `.R` it will use `script:`.
Therefore, in addition edit your script/notebook to use the values passed to it by snakemake. E.g. for a python script/notebook:

```python
## input
in_path = str(snakemake.input.in_path)

## output
out_path = str(snakemake.output.out_path)

## params
number = float(snakemake.params.number)
string = str(snakemake.params.string)
a_list = list(snakemake.params.a_list)
```

## config file

The config file allows flexible adjustment of multiple pipeline runs with different parameters (even rewiring the order of steps without changes to the Snakefile).
Default parameters are added unter defaults. In addition, a list of `runs` is specified at the bottom of the file, which can be used to overwrite specific parameters per run, and add additional runs.
(TODO: add more explanation)

Example:

```yaml
general_settings:
    result_dir: "results/"
    notebook_dir: "notebooks/"
    execute_runs: &exec_runs
        - all
        - new_run

rules:
    Step1:
        execute_runs: *exec_runs
        default_params:
            input_in_path: /path/to/infile.txt
            number: 123
            string: text
            a_list: ["a", "b", "c"]

runs:
    all: {}
    new_run:
        Step1:
            number: 321
```
