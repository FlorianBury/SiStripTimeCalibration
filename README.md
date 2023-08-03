# Setup

## CMSSW

Current CMSSW release : CMSSW_12_5_0

```
[CMSSW initialization]
cmsrel CMSSW_12_5_0
git cms-addpkg SimTracker
[cd to this git repo]
cp -r cmssw/SiPhase2TimingCalibration <path to CMSSW>/src/Simtracker/
```

## Environment
First, one must create the conda environment. To do so, simply run 
```
    conda env create -n timing --file ENV.yml
```
Then one must install the timing scripts as a pip package (called `timeCal`). This is suboptimal for now, as the best solution should be a conda install but will leave that for the future.  The classic pip install might fail because the path of the package might not be recognized by conda, instead one can use the dev mode as below
```
    export SETUPTOOLS_ENABLE_FEATURES=legacy-editable
    pip install -e .
```

After these steps, only 
```
    conda activate timing
```
need to be used in the future


## Global config 

To specify the paths and several other global parameters of the scripts, put the following files as `~/.config/timerc` :
```
[paths]
cmssw       = <path to CMSSW subdirectory of SiPhase2TimingCalibration/test>
production  = <path to put the BX histograms root file (can be heavy, so large storage is recommended)>
scans       = <path to put the scan results (can be heavy, so large storage is recommended)>
calibration = <path to put the calibration results root file (can be heavy, so large storage is recommended)>

[cmssw]
init = <necessary command to initialize the CMSSW environment on your cluser>
# For example on Ingrid-ui1 at CP3 (louvain) : module load cms/cmssw && eval `scramv1 runtime -sh`
```

And you are good to go !

# Running the CMSSW production 

Typically two scripts need to be used to produce the ROOT files : the production script (eg PUCalibration_cfg.py) and the harvester (Harvester_cfg.py). Only the latter is fixed, the former is left to be provided by the user. 

The chain of these two scripts has been automatized within the CLI command `BXRun`. It can either be used "as in" to run a production, or to run multiple times based on a config through Dask. Both cases will be covered below.

## Simple run 

To run on a single set of parameters, simply provide the parameters as you would to the CMSSW script
```
    BXRun --script PUCalibration_cfg.py --run N=1 threshold=5000 pileup=200 HSfile=<path to txt file> PUfile=<path to txt file> -o <directory path> 
```
The script will take care to run both CMSSW script in the subdirectory, and use default values for the parameters that have been omitted.

### Note on files

To use different files for the HS (hard scattering) and pileup, use the following arguments 
```
--HSFile <path_to_txt> --PUFile <path_to_txt>
```
where the txt file is a list of GEN-SIM files 

## Multiple parameters
The same command can be used to run in parallel the production of multiple histograms using Dask. 

The necessary arguments are :
- `--yaml` : the path to a YAML config (see below)
- `--dask` : the dask mode to run (`local` to run in parallel on the session, or `slurm`/`htcondor` to run on a cluster) 

Command example :
```
    BXRun --yaml my_config.yml --script PUCalibration_cfg.py --dask slurm -o my_output_path
```

### Config file 
The config file provides all information for the production to be run. For each parameter taken by the CMSSW production script, either one of more values can be provided. For example 

```yaml
pt: [0,2]
threshold: [4000,5000,6000]
N: 100
pileup: [0,200]
```

### What the script produces
The script will produce all combinations, inform you of the number of jobs and start the processing. 

Note : if you use the `--debug` argument, no job will be sent and an interactive shell will start to let you make more checks (you can exit by typing `exit` or using CTRL-D, the script will stop)

If the `-o/--output` path is absolute, the result will be put there. If not, the path will be interpreted as a subdirectory to be created in the `production` part of your `timerc`.

In this directory you will find the following subdirectories :
- `infiles` : a copy of your config file, this is the one that will be used if you run the command again
- `results` : where your output files will be, in subdirectories

Note : the first time the command is run, the config is copied in `infiles`. If you rerun the command the `--yaml` argument will be ignored, and you must modify the one in `infiles` to change the parameters. 

### Monitoring loop 

In this mode, a monitoring loop is started to show the progress of the code. A prompt will wait for any user modification, just type `help` to see what options are available.

At every loop (whose duration is by default 60s, use the `interval` command in the console to modify it), the following steps are done :
- Try to resubmit failed tasks (can be done manually with `retry`).
- Clean the already finished tasks (can be done manually with `clean`). NB : in practice the futures are replaced by Dummies to let Dask cleanup the actual futures memory.
- Printout the status of the jobs for each task (see tasks note below).
- Printout status of the cluster (workers correspond to what Dask has asked, threads and cores to what is actually running at the moment).
- Open the interactive prompt for the user.

At the end of the comptations, if all the jobs are finished they will be aggregated into the `<output_dir>/results` directory. If not, the prompt will wait for the user to do something : exit, check the futures, etc.

# Scan plots

