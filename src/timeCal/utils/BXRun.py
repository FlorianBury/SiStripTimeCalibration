import os
import sys
import copy
import json
import yaml
import math
import glob
import functools
import itertools
import argparse
import subprocess
import numpy as np
import ROOT
from pprint import pprint
from IPython import embed

from .environment import getEnv
from .dask_utils import MonitoringLoop
from .logger import Logger
from .yamlLoader import parseYaml
from .scan_utils import makeScan

DEFAULT_PARAMS = {
    'N'                  : 1,
    'pileup'             : 200,
    'pt'                 : 2.,
    'threshold'          : 5800,
    'thresholdsmearing'  : 0.,
    'tofsmearing'        : 0.,
    'mode'               : 'scan',
    'subdet'             : 'ALL',
    'offset'             : -1.,
    'verbose'            : 0,
}

SETUP_CMSSW = getEnv()['cmssw']['init']
CMSSW_DIR = os.path.join(getEnv()['paths']['cmssw'])
HARVESTER_SCRIPT = 'Harvester_cfg.py'
OUTPUT_DIR = getEnv()['paths']['production']

class Task:
    def __init__(self,script,subdir,params,worker=False,verbose=False):
        self.script = os.path.join(CMSSW_DIR,script)
        if not os.path.exists(self.script):
            raise RuntimeError(f'Cannot find script {self.script}')
        self.params = {**DEFAULT_PARAMS,**params}
        if os.path.isabs(subdir):
            self.subdir = subdir
        else:
            self.subdir = os.path.join(OUTPUT_DIR,subdir)
        if not os.path.exists(self.subdir):
            os.makedirs(self.subdir)
        self.logger = Logger('Task','debug' if (verbose or worker) else 'info','both' if worker else 'file',self.subdir)
        if len(glob.glob(os.path.join(self.subdir,'BXHist*_harvested.root'))) > 0:
            self.logger.warning(f'Already harvested ROOT files in {self.subdir}')
        else:
            self.run()

    @staticmethod
    def in_virtualenv():
        # Get base/real prefix, or sys.prefix #
        # Check if matches with sys.prefix #
        if hasattr(sys, "base_prefix"):
            return sys.base_prefix != sys.prefix
        elif hasattr(sys, "real_prefix"): # old versions
            return sys.real_prefix != sys.prefix
        else:
            return False

    def get_env(self):
        env = os.environ.copy()
        if self.in_virtualenv():
            # If in virtual environment, gotta forge a copy of the environment, where we:
            # Delete the VIRTUAL_ENV variable.
            del(env['VIRTUAL_ENV'])

            # Delete the venv path from the front of my PATH variable.
            orig_path = env['PATH']
            virtual_env_prefix = sys.prefix + '/bin:'
            env['PATH'] = orig_path.replace(virtual_env_prefix, '')
        return env


    def run(self):
        args = [f"{k}={v}" for k,v in self.params.items()]
        self.logger.info('Starting the DQM file production')
        self.logger.info('Arguments : '+' '.join(args))
        dqm_cmd = self.format_command(['cmsRun',self.script] + args, wdir=self.subdir)
        self.logger.debug(f'Command: {dqm_cmd}')
        rc,output = self.run_command(dqm_cmd,return_output=True,shell=True,env=self.get_env())
        self.logger.info(f'... exit code : {rc}')
        if rc != 0:
            msg = "Failed to produce the DQM root file :\n"
            for line in output:
                msg += line + "\n"
            raise RuntimeError(msg)
        dqm_file = None
        for line in output:
            self.logger.debug(line)
            if 'BXHist' in line and '.root' in line:
                for l in line.split():
                    if '.root' in l:
                        dqm_file = l
                if dqm_file is not None:
                    break
        if dqm_file is None or not '.root' in dqm_file:
            raise RuntimeError(f"Wrong output root file : {dqm_file}")
        else:
            dqm_file = os.path.join(self.subdir,dqm_file)

        self.logger.info(f"DQM root file created as {dqm_file}")
        if not os.path.exists(dqm_file):
            raise RuntimeError("DQM root file not present")

        self.logger.info('Starting harvesting')
        harvest_cmd = self.format_command(['cmsRun',os.path.join(CMSSW_DIR,HARVESTER_SCRIPT),f'input={dqm_file}'],wdir=self.subdir)
        self.logger.debug(f'Command: {harvest_cmd}')
        rc = self.run_command(harvest_cmd,shell=True,env=self.get_env())

        self.logger.info(f'... exit code : {rc}')
        if rc != 0:
            msg = "Harvesting failed :\n"
            for line in output:
                msg += line + "\n"
            raise RuntimeError(msg)

        self.logger.info('Starting renaming')
        hist_file = dqm_file.replace('raw','harvested')
        dirname = os.path.dirname(dqm_file)
        rename_cmd = ['mv',os.path.join(self.subdir,'DQM_V0001_R000000001__Global__CMSSW_X_Y_Z__RECO.root'),hist_file]
        rc = self.run_command(rename_cmd)
        if rc != 0:
            raise RuntimeError("Could not rename the harvested file")
        self.logger.info(f'... exit code : {rc}')
        self.logger.info(f'Renamed to {hist_file}')

        self.logger.info ('Starting cleaning')
        clean_cmd = ['rm', dqm_file]
        rc = self.run_command(clean_cmd)
        if rc != 0:
            raise RuntimeError("Could note clean intermediate root file")
        self.logger.info (f'... exit code : {rc}')

        # Save parameters in json #
        param_file = os.path.join(self.subdir,'params.json')
        with open(param_file,'w') as handle:
            json.dump(self.params,handle,indent=4)
        self.logger.info(f'Saved parameters to {param_file}')

        # Save parameters in root file #
        F = ROOT.TFile(hist_file,"UPDATE")
        for name,arg in self.params.items():
            p = ROOT.TNamed(name,str(arg))
            p.Write()
        F.Close()

        # Save logger #
        #log_file = os.path.join(self.subdir,'log.out')
        #self.logger.info(f'Saved log in {log_file}')
        #self.logger.write(log_file)


    @staticmethod
    def format_command(cmd,wdir=None):
        full_cmd = f"cd {CMSSW_DIR}"
        if len(SETUP_CMSSW) > 0:
            full_cmd += f" && {SETUP_CMSSW}"
        if wdir is None:
            wdir = os.getcwd()
        full_cmd += f" && cd {wdir}"
        if isinstance(cmd,str):
            full_cmd += f" && {cmd}"
        elif isinstance(cmd,list):
            full_cmd += f" && {' '.join(cmd)}"
        else:
            return ValueError
        return full_cmd

    @staticmethod
    def run_command(command,return_output=False,**kwargs):
        process = subprocess.Popen(command,universal_newlines=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**kwargs)
        # Poll process for new output until finished #
        output = []
        while True:
            try:
                nextline = process.stdout.readline()
            except UnicodeDecodeError:
                continue
            if nextline == '' and process.poll() is not None:
                break
            nextline = nextline.strip()
            if len(nextline) == 0:
                continue
            if return_output:
                output.append(nextline)
        process.communicate()
        exitCode = process.returncode
        if return_output:
            return exitCode,output
        else:
            return exitCode


class Scan:
    def __init__(self,script,output,logger,yaml_path=None):
        self.script = script
        self.output = output
        self.logger = logger
        self.yaml_path = yaml_path
        self.paramDict = self.getConfigContent()
        self.paramNames, self.paramValues = makeScan(self.paramDict)
        self.logger.info('Parameters for scan :')
        for pName in self.paramNames:
            self.logger.info(f'... {pName:30s}: {self.paramDict[pName]}')
        self.args = self.makeDaskArgs()

    def getConfigContent(self):
        saved_cfg_path = os.path.join(self.outputPaths['infiles'],'config.yml')
        if os.path.exists(saved_cfg_path):
            self.logger.info(f'Taking config file from output directory {saved_cfg_path}')
            path = saved_cfg_path
        else:
            if self.yaml_path is None:
                raise RuntimeError(f'You should provide a yaml config')
            self.logger.info('Taking config file from input {self.yaml_path}')
            path = self.yaml_path

        config = parseYaml(path)
        if not os.path.exists(saved_cfg_path):
            with open(saved_cfg_path,'w') as handle:
                yaml.dump(config,handle)
            self.logger.info(f'Saved config in {path}')
        return config

    @functools.cached_property
    def outputPaths(self):
        mainDir = os.path.join(OUTPUT_DIR,self.output)
        outputPaths = {'main': mainDir}
        outputPaths["infiles"] = os.path.join(mainDir, "infiles")
        outputPaths["results"] = os.path.join(mainDir, "results")
        for path in outputPaths.values():
            if not os.path.exists(path):
                os.makedirs(path)
        return outputPaths

    def makeDaskArgs(self):
        # Make list of params dicts #
        fullParams = [{pN:pV for pN,pV in zip(self.paramNames,paramValues)} for paramValues in self.paramValues]
        # check with what has been produced already #
        subdirNums = []
        for subdir in glob.glob(self.outputPaths['results']+'/*'):
            # Check root file #
            r_files = glob.glob(os.path.join(subdir,'*harvested*root'))
            if len(r_files) == 0:
                continue
            # Check parameters #
            p_file = os.path.join(subdir,'params.json')
            if os.path.exists(p_file):
                with open(p_file,'r') as handle:
                    p_in_file = json.load(handle)
                p_in_file = {k:v for k,v in p_in_file.items() if k in self.paramNames}
                if p_in_file in fullParams:
                    fullParams.remove(p_in_file)
                    self.logger.debug(f'Found set of params already in {subdir}')
                    subdirNums.append(os.path.basename(subdir))
        self.logger.info(f'Submitting {len(fullParams)} tasks')
        # Make the args #
        args = [[self.script]*len(fullParams),[None]*len(fullParams),[None]*len(fullParams)]
        subdirNum = 0
        for i,param in enumerate(fullParams):
            while str(subdirNum) in subdirNums:
                subdirNum += 1
            subdirNums.append(str(subdirNum))
            args[1][i] = os.path.join(self.outputPaths['results'],str(subdirNum))
            args[2][i] = param
        return args

    def getParameters(self):
        return [{pName:pVal for pName,pVal in zip(self.paramValuesNames,params)} for params in self.paramValues]


def main():
    parser = argparse.ArgumentParser(description='Timing calibration setup')
    parser.add_argument('--script',action='store',required=True,type=str,
                        help='Name of the script in the CMSSW directory to run')
    parser.add_argument('-o','--output',action='store',required=True,type=str,default=None,
                        help='Name of subdir output directory (will be put in the `production` output directory)')
    parser.add_argument('--yaml',action='store',required=False,type=str,default=None,
                        help='Config to run several modes')
    parser.add_argument('--dask',action='store',required=False,type=str,default='local',
                        help='Dask mode')
    parser.add_argument('--run',nargs='*',required=False,type=str,default=None,
                        help='Run parameters (with `=` between name of the arg and the value)')
    parser.add_argument('-v','--verbose',action='store_true',default=False,
                        help='Debug logger mode')
    parser.add_argument('--debug',action='store_true',default=False,
                        help='Does not start the cluster')
    args = parser.parse_args()

    # Logger #
    logger = Logger('BXRun','debug' if args.verbose else 'info','console')
    # Local mode #
    if args.run is not None:
        if args.yaml is not None:
            raise RuntimeError(f'Cannot use both --run and --yaml')
        run_params = {arg.split("=")[0]:arg.split("=")[1] for arg in args.run}
        logger.info('Running in local mode with the following parameters :')
        for p_name,p_val in run_params.items():
            logger.info(f'... {p_name} = {p_val}')
        task = Task(
            script = args.script,
            subdir = args.output,
            params = run_params,
            worker = True,
            verbose = args.verbose,
        )
    # Dask mode #
    else:
        scan = Scan(args.script,args.output,logger,args.yaml)
        if args.debug:
            logger.info('Entering debug mode, nothing will be submitted')
            embed()
            sys.exit(0)
        # Start cluster #
        if args.dask == 'local':
            from dask.distributed import LocalCluster
            cluster = LocalCluster(n_workers=10,threads_per_worker=1,memory_limit='6GiB',scheduler_port=1234)
        elif args.dask == 'slurm':
            from dask_jobqueue import SLURMCluster
            cluster = SLURMCluster()
        elif args.dask == 'htcondor':
            from dask_jobqueue import HTCondorCluster
            cluster = HTCondorCluster()
        else:
            raise NotImplementedError(f'Dask mode {args.dask} not implemented')
        # Start client #
        from dask.distributed import Client
        client = Client(cluster)
        # Submit and run loop #
        futures = client.map(Task,*scan.args)
        loop = MonitoringLoop(futures,client,cluster,logger,60)
        loop.start(5)



if __name__ == '__main__':
    main()



