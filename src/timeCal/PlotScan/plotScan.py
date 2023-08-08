#!/usr/bin/env python3

import os
import re
import sys
import yaml
import json
import glob
import ROOT
import argparse
import itertools
from pprint import pprint
from tqdm import tqdm
from copy import copy,deepcopy
from IPython import embed
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import cm

from .data_helper import Data, Observable

from ..utils.yamlLoader import parseYaml
from ..utils.environment import getEnv
from ..utils.context import TFileOpen
from ..utils.scan_utils import makeScan
from ..utils.logger import Logger

OBSERVABLES = ['Efficiency',
               'Fire rate',
               'Out-of-time fraction',
               'Mean',
               'Next BX contamination',
               'Previous BX contamination']
RANGES = {'Efficiency'                 : (0.,1.),
          'Fire rate'                  : (0.,1.),
          'Out-of-time fraction'       : (0.,1.),
          'Mean'                       : (-1.,1.),
          'Next BX contamination'      : (0.,1.),
          'Previous BX contamination'  : (0.,1.)}


try:
    ROOT_VERSION = re.split("\.|/",ROOT.__version__)
except:
    ROOT_VERSION = None

class FileProcessor:
    def __init__(self,hists,efficiency,firerate,labels):
        self.hists      = hists
        self.efficiency = efficiency
        self.firerate   = firerate
        self.labels     = labels

    def __call__(self,f):
        # Open file #
        if not os.path.exists(f):
            raise RuntimeError(f'File {f} does not exist')
        json_path = os.path.join(os.path.dirname(f),'params.json')
        if not os.path.exists(json_path):
            raise RuntimeError(f'File {json_path} does not exist')
        params_json = self._getParametersFromJson(json_path)
        with TFileOpen(f,'r') as F:
            # Get file parameters #
            #params_root = self._getParametersFromTFile(F)
            #if params_json != params_root:
            #    raise RuntimeError(f'Difference between parameters in ROOT file {f} ({params_root}) and json {json_path} ({params_json}), this should not happen')

            # Produce efficiency hist#
            h_eff = self._getEfficiencyHist(F)
            h_fire = self._getFireRate(F)

            # Loop over each histogram #
            content = []
            for name,values in self.hists.items():
                # Initialize entry #
                entry = {}
                for key,val in params_json.items():
                    if key in self.labels.keys():
                        key = self.labels[key]
                    try:
                        val = float(val)
                    except ValueError:
                        pass
                    entry[key] = val
                entry.update(values)
                delay = values['delay']

                # Get efficiency #
                eff,contNext,contPrev = self._getEfficiencyValues(h_eff,delay)
                entry['Efficiency'] = eff
                entry['Next BX contamination'] = contNext
                entry['Previous BX contamination'] = contPrev

                # Get firerate #
                entry['Fire rate'] = self._getFireRateValue(h_fire,delay)

                # Get histogram #
                h = self._getHistogram(F,values['dir'],name)

                # Get content in numpy arrays #
                e,w,s = self._getHistContent(h)

                # Compute additional info based on histogram #
                fo,fo_err = self._fracOutHisto(e,w,s)
                entry['Out-of-time fraction'] = fo
                entry['Out-of-time fraction error'] = fo_err
                m,m_err = self._meanHisto(e,w,s)
                entry['Mean'] = m
                entry['Mean error'] = m_err

                # Save entry in content #
                content.append(entry)

        # return #
        return content

    @staticmethod
    def _getHistogram(F,dir_path,name):
        # Get through subdirectories by recurrence #
        subdir = F
        for sub in dir_path.split('/'):
            if ROOT_VERSION is not None and int(ROOT_VERSION[1]) >= 22:
                if not hasattr(subdir,sub):
                    raise RuntimeError(f'Could not find subdirectory `{sub}` from `{subdir}` in file {F.GetName()}')
                subdir = getattr(subdir,sub)
            else:
                subdir = subdir.Get(sub)
        if not subdir.GetListOfKeys().FindObject(name):
            raise RuntimeError(f'Could not find histogram `{name}` from subdir `{subdir}` in file `{F.GetName()}`')
        return subdir.Get(name)

    def _getParametersFromTFile(self,F):
        params = {}
        for pFile,pName in self.labels.items():
            if not F.GetListOfKeys().FindObject(pFile):
                raise RuntimeError(f'Could not find parameter `{pFile}` in file `{F.GetName()}`')
            params[pName] = float(F.Get(pFile).GetTitle())
        return params

    def _getParametersFromJson(self,f):
        with open(f,'r') as handle:
            params = json.load(handle)
        return params

    def _getEfficiencyHist(self,F):
        h_true = self._getHistogram(F,self.efficiency['dir'],self.efficiency['truth'])
        h_reco = self._getHistogram(F,self.efficiency['dir'],self.efficiency['reco'])
        h_eff  = h_reco.Clone("eff")
        h_eff.Divide(h_true)
        return h_eff

    def _getFireRate(self,F):
        h_true = self._getHistogram(F,self.firerate['dir'],self.firerate['truth'])
        h_reco = self._getHistogram(F,self.firerate['dir'],self.firerate['reco'])
        h_fire = h_reco.ProjectionY("fire",firstxbin=2) # BX = 0 -> no hit
        h_true = h_true.ProjectionY("",
                                    firstxbin  = h_true.GetXaxis().FindBin(0.),
                                    lastxbin   = h_true.GetXaxis().FindBin(0.))
        h_fire.Divide(h_true)
        return h_fire

    @staticmethod
    def _getEfficiencyValues(h_eff,delay):
        # Get the bins we are interested in #
        bin_delay   = h_eff.GetYaxis().FindBin(delay)
        bin_center  = h_eff.GetXaxis().FindBin(0)
        bin_next    = h_eff.GetXaxis().FindBin(1)
        bin_prev    = h_eff.GetXaxis().FindBin(-1)
        # Compute values #
        eff         = h_eff.GetBinContent(bin_center,bin_delay) # Efficiency for this BX
        contNext    = h_eff.GetBinContent(bin_next,bin_delay)   # Contamination in next BX
        contPrev    = h_eff.GetBinContent(bin_prev,bin_delay)   # Contamination in previous BX
        return eff,contNext,contPrev

    @staticmethod
    def _getFireRateValue(h_fire,delay):
        return h_fire.GetBinContent(h_fire.GetXaxis().FindBin(delay))

    @staticmethod
    def _getHistContent(h):
        e = [h.GetXaxis().GetBinUpEdge(0)]
        w = []
        s = []
        for i in range(1,h.GetNbinsX()+1):
            e.append(h.GetXaxis().GetBinUpEdge(i))
            w.append(h.GetBinContent(i))
            s.append(h.GetBinError(i))
        return np.array(e),np.array(w),np.array(s)

    @staticmethod
    def _fracOutHisto(e,w,s):
        c = (e[:-1]+e[1:])/2
        idx = np.delete(np.arange(w.shape[0]),np.abs(c).argmin())
        return w[idx].sum()/w.sum(),np.sqrt((s[idx]**2).sum())/w.sum()

    @staticmethod
    def _meanHisto(e,w,s):
        c = (e[:-1]+e[1:])/2
        return (w*c).sum()/w.sum(),np.sqrt(((s*c)**2).sum())/w.sum()



class PlotScan:
    def __init__(self,input,output,hists,parameters,labels,observables,efficiency,firerate,mode,force,logger,**kwargs):
        # Attributes #
        self.input          = input
        self.output         = output
        self.labels         = labels
        self.mode           = mode
        self.force          = force
        self.cache          = os.path.join(getEnv()['paths']['scans'],'cache',f'cache_{self.output}.pkl')
        self.logger         = logger

        # Path #
        if not os.path.isabs(input):
            self.path = os.path.join(getEnv()['paths']['production'],input)
        else:
            self.path = path

        # Observables and ranges #
        if observables is None:
            self.observables = OBSERVABLES
            self.ranges      = RANGES
        else:
            self.observables,self.ranges = [],{}
            for obs in observables:
                if obs not in OBSERVABLES:
                    error_line =  f'Observable name `{obs}` is not defined, available observables are :\n'
                    for OBSERVABLE in OBSERVABLES:
                        error_line += f'... {OBSERVABLE}\n'
                    raise RuntimeError(error_line)
                self.observables.append(obs)
                self.ranges[obs] = RANGES[obs]

        # Scan parameters #
        self.paramNames, self.paramValues = makeScan(parameters)
        self.files = self.getFilePaths()

        # Make processor and get content #
        self.processor = FileProcessor(hists,efficiency,firerate,labels)
        self.getFullContent()

    def getFilePaths(self):
        files = []
        paramEntries = [{k:v for k,v in zip(self.paramNames,paramValues)} for paramValues in self.paramValues]
        for subdir in glob.glob(os.path.join(self.path,'results','*')):
            # get params #
            json_path = os.path.join(subdir,'params.json')
            if not os.path.exists(json_path):
                self.logger.warning(f'File {json_path} is missing, this might not be expected')
                continue
            with open(json_path,'r') as handle:
                params = json.load(handle)
            # get file name if in the parameters #
            idx = None
            for i,paramEntry in enumerate(paramEntries):
                if paramEntry.items() <= params.items():
                    idx = i
            if idx is not None:
                # Mark and cleanup for faster loop #
                del paramEntries[idx]
                # get file #
                rfiles = glob.glob(os.path.join(subdir,'BX*harvested.root'))
                if len(rfiles) == 0:
                    self.logger.warning(f'ROOT file absent in {subdir}, this might not be expected')
                elif len(rfiles) == 1:
                    files.append(rfiles[0])
                else:
                    raise RuntimeError(f'More than one harvested root file in {subdir}, this might lead to bugs')
                files.append(rfiles[0])
        if len(paramEntries) > 0:
            self.logger.warning('Missing parameters :')
            for paramEntry in paramEntries:
                if pBool:
                    self.logger.warning('...')
                    for pName, pVal in paramEntry.items():
                        self.logger.warning(f'\t{pName:30s} : {pVal}')
            raise RuntimeError('See missing parameters above')
        return files

    def getFullContent(self):
        if not os.path.exists(self.cache) or self.force:
            if self.force:
                self.logger.info('Forcing recreation of the cache')
            else:
                self.logger.info('No cache file present, will process root files')

            # Just check that files are there #
            for f in self.files:
                if not os.path.exists(f):
                    self.logger.warning(f'Could not find file : {f}')

            # Serial working #
            content = []
            if self.mode == 'worker':
                for f in tqdm(self.files):
                    content.extend(self.processor(f))
            # Parallel working #
            else:
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
                    raise NotImplementedError(f'Dask mode {args.mode} not implemented')
                # Start client #
                from dask.distributed import Client
                client = Client(cluster)
                # submit #
                def func(processor,f):
                    return processor(f)
                futures = client.map(func,[self.processor]*len(self.files),self.files)
                loop = MonitoringLoop(futures,client,cluster,logger,60)
                loop.start()
                #pool = mp.Pool(self.jobs)
                #for content in pool.imap(self.processor,self.files):
                #    pbar.update()
                #    self.content.extend(content)
                #pool.close()
                #pool.join()
            df = pd.DataFrame(content)
            df.to_pickle(self.cache)
            self.logger.info(f'Saved cache in {self.cache}')
        else:
            df = pd.read_pickle(self.cache)
            self.logger.info(f'Loaded cache from {self.cache}')
        self.logger.info('Producing data object from the pandas DataFrame')
        self.data = Data(df)
        self.logger.info('... done')
        self.data.SetParameters(list(self.labels.values()) + ['delay'])

    def Plots(self):
        path_plots = os.path.join(getEnv()['paths']['scans'],'plots',self.output)
        path_data  = os.path.join(getEnv()['paths']['scans'],'data',self.output)
        if not os.path.exists(path_plots):
            os.makedirs(path_plots)
        if not os.path.exists(path_data):
            os.makedirs(path_data)
        for obsName in self.observables:
            observable = self.data.GetObservable(obsName)
            for param in self.labels.values():
                self.logger.info(f"Plotting {obsName} curves of {param} parameter")
                output_plots_dir = os.path.join(path_plots,f'curves_{obsName}_{param}'.replace(' ',''))
                output_data_dir = os.path.join(path_data,f'curves_{obsName}_{param}'.replace(' ',''))
                if not os.path.exists(output_plots_dir):
                    os.makedirs(output_plots_dir)
                if not os.path.exists(output_data_dir):
                    os.makedirs(output_data_dir)

                labels_to_vary = {key:observable.GetLabels()[key] for key in observable.GetLabels().keys() if key != param and key != 'delay'}

                for comb in itertools.product(*list(labels_to_vary.values())):
                    varied_labels = {k:c for k,c in zip(labels_to_vary.keys(),comb)}
                    obs2d = observable.GetSlice(**varied_labels)
                    try:
                        data_dict = {'2D':obs2d.GetRootTGraph2D(x='delay',y=param)}
                    except:
                        from IPython import embed; embed()
                    fig_name = f'{"_".join([f"{p}_{v}" for p,v in varied_labels.items()])}'.replace(' ','_')

                    # Plot 1D #
                    fig, ax = plt.subplots(figsize=(8,7))
                    plt.subplots_adjust(left=0.15, right=0.90, top=0.85, bottom=0.12)
                    paramValues = obs2d.GetLabels()[param]
                    colors = cm.jet(np.linspace(0,1,paramValues.shape[0]))
                    for paramVal,color in zip(paramValues,colors):
                        obs1d = obs2d.GetSlice(**{param:paramVal})
                        obs1d.Pyplot1D(ax,color=color)
                        data_dict[f'1D_{param}_{paramVal}'] = obs1d.GetRootTGraph()
                    sm = cm.ScalarMappable(cmap=cm.rainbow, norm=plt.Normalize(vmin=paramValues.min(), vmax=paramValues.max()))
                    cbar = plt.colorbar(sm)
                    cbar.set_label(param,fontsize=18,labelpad=20)
                    cbar.ax.tick_params(labelsize=14)
                    plt.xlabel('Delay [ns]',fontsize=18,labelpad=20)
                    plt.ylabel(obsName,fontsize=18,labelpad=10)
                    plt.ylim(self.ranges[obsName])
                    title = f'{param} curves\n({", ".join([f"{p} = {v}" for p,v in varied_labels.items()])})'
                    plt.title(title,fontsize=20,pad=25)
                    plt.tick_params(axis='both', which='major', labelsize=14)
                    self.logger.info('... '+title.replace("\n"," : "))
                    fig.savefig(f'{os.path.join(output_plots_dir,fig_name)}_1D.png')
                    plt.close()

                    # Plot 2D #
                    fig,ax = plt.subplots(figsize=(8,7))
                    plt.subplots_adjust(left=0.17, right=0.95, top=0.85, bottom=0.1)
                    obs2d.Pyplot2D(x='delay',y=param, ax=ax, vmin=self.ranges[obsName][0], vmax=self.ranges[obsName][1], shading='auto', linewidth=0,rasterized=True)
                    cbar = fig.colorbar(ax.collections[0])
                    cbar.set_label(obsName,fontsize=18,labelpad=20)
                    cbar.ax.tick_params(labelsize=14)
                    ax.set_xlabel('Delay [ns]',fontsize=18,labelpad=10)
                    ax.set_ylabel(param,fontsize=18,labelpad=20)
                    ax.set_title(title,fontsize=20,pad=25)
                    ax.tick_params(axis='both', which='major', labelsize=14)
                    fig.savefig(f'{os.path.join(output_plots_dir,fig_name)}_2D.png')
                    plt.close()

                    # Save in ROOT file #
                    with TFileOpen(f'{os.path.join(output_data_dir,fig_name)}.root','w') as F:
                        for name,obj in data_dict.items():
                            obj.Write(name)

def main():
    parser = argparse.ArgumentParser(description='Produce datacards')
    parser.add_argument('--yaml', action='store', required=True, type=str,
                        help='Yaml containing parameters')
    parser.add_argument('--custom', action='store', required=False, default=None, nargs='*',
                        help='Format the yaml file')
    parser.add_argument('-i','--input',action='store',required=True,type=str,
                        help='Name of subdir input directory')
    parser.add_argument('-o','--output',action='store',required=True,type=str,
                        help='Name of subdir output directory')
    parser.add_argument('--observables', action='store', required=False, default=None, nargs='*',
                        help='List of observables to restrict the plotting to [default = all]')
    parser.add_argument('-v','--verbose', action='store_true', required=False, default=False,
                        help='Verbose mode')
    parser.add_argument('--cache', action='store_true', required=False, default=False,
                        help='Force recreation of the cache (and no plots)')
    parser.add_argument('--mode',action='store',required=False,type=str,default='worker',
                        help='Processing mode : worker (in series) or dask modes = local | slurm | htcondor')
    args = parser.parse_args()

    # Make logger #
    logger = Logger('scan','info' if not args.verbose else 'debug','console')

    if args.yaml is None:
        raise RuntimeError("Must provide the YAML file")
    f = parseYaml(args.yaml,args.custom)

    instance = PlotScan(**f,input=args.input,output=args.output,mode=args.mode,force=args.cache,observables=args.observables,logger=logger)
    if not args.cache:
        instance.Plots()



if __name__ == "__main__":
    main()

