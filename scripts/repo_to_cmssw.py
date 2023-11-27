## repo_to_cmssw.py
## 27.11.23
## if we want to move all changes from our repo to the corresponding cmssw directory where things are built/executed

from argparse import ArgumentParser
import os

files_to_copy = ['plugins/Phase2TrackerBXHistogram.cc',
                 'plugins/Phase2TrackerBXHistogram.h',
                 'python/Phase2TrackerBXHistogram_cfi.py',
                 'test/Harvester_cfg.py',
                 'test/PUCalibration_cfg.py',
                 'test/PythiaGunCalibration_cfg.py']
                 
def copy_file(file, dir1, dir2):
    ''' copy file to target directory
    remember dir1 = repo, dir2 = cmssw '''
    os.system(f'cp {dir1}/{file} {dir2}/{file}')
    
def main(dir1, dir2, lxplus_naf):
    
    if lxplus_naf == 'naf':
        lxplus_naf_dir = "/nfs/dust/cms/user/sanjrani/Tracker"
        if (dir1 == None) or (dir2==None):
            dir1 = f"{lxplus_naf_dir}/SiStripTimeCalibration/cmssw/SiPhase2TimingCalibration"
            dir2 = f"{lxplus_naf_dir}/CMSSW_12_5_0/src/SimTracker/SiPhase2TimingCalibration"
    elif lxplus_naf == 'lxplus':
        lxplus_naf_dir = "/eos/user/m/msanjran/TrackerDev"
        if (dir1 == None) or (dir2==None):
            dir1 = f"{lxplus_naf_dir}/SiStripTimeCalibration/cmssw/SiPhase2TimingCalibration"
            dir2 = f"{lxplus_naf_dir}/CMSSW_12_5_0/src/SimTracker/SiPhase2TimingCalibration"
    
    print("-"*20)
    print(f"Copying from dir1 to dir2")
    print(f"Dir 1: {dir1}")
    print(f"Dir 2: {dir2}")
    print(f"Files: {files_to_copy}")
    for file in files_to_copy:
        copy_file(file, dir1, dir2)
        
    print(f"Done")
    print("-"*20)

if __name__ == '__main__':
    
    parser = ArgumentParser()

    parser.add_argument("-d1", "--dir1", type=str, default=None,
                        help="Path to directory 1.")
    
    parser.add_argument("-d2", "--dir2", type=str, default=None,
                        help="Path to directory 2.")

    parser.add_argument("-ln", "--lxplus_naf", type=str, default='naf', choices=['naf','lxplus'],
                        help="What system we're on to copy it easily")
                        
    main(**parser.parse_args().__dict__)
