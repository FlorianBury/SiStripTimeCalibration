## check_dask_output.py
## 28.11.23
## check if all the root files in the output are harvested

from argparse import ArgumentParser
import glob
import os
from tqdm import tqdm
import json

def get_output_dirs(input_dir):
    ''' don't need to specify that it's results, we do that here '''
    dir_list = glob.glob(f"{input_dir}/results/*")
    return dir_list
    
def look_for_harvested(output_dir):
    ''' look inside one of these output dirs for a ..._harvested.root file '''
    files = glob.glob(f"{output_dir}/*_harvested.root")
    if len(files) > 0:
        return True
    return False
    
def look_for_nonempty_json(output_dir):
    ''' look inside one of the output dirs for a params.json file '''
    files = glob.glob(f"{output_dir}/params.json")
    if len(files) > 0:
        for file_path in files:
            try:
                with open(file_path, 'r') as file:
                    content = json.load(file)
            except:
                print(f"Failed json: {file_path}")
                return False
            return True
    return False
    
    
def main(input_dir, check_json):

    print("-"*20)
    print(f"Checking number of successful scans")
    print(f"Input directory: {input_dir}")
    
    output_directories = get_output_dirs(input_dir)
    print(f"N. output directories: {len(output_directories)}")
    n_harvested = 0
    n_json = 0
    for output_dir in tqdm(output_directories):
        has_harvested = look_for_harvested(output_dir)
        if has_harvested:
            n_harvested += 1
        if check_json:
            nonempty_json = look_for_nonempty_json(output_dir)
            if nonempty_json:
                n_json += 1
                
    print(f"N. harvested files: {n_harvested}")
    print(f"{(n_harvested/len(output_directories))*100}% of runs successful")
    
    if check_json:
        print(f"N. non empty json files: {n_json}")
        print(f"{(n_json/len(output_directories))*100}% of produced json files")
    
    print(f"Done")
    print("-"*20)
    
if __name__ == '__main__':
    
    parser = ArgumentParser()

    parser.add_argument("-i", "--input_dir", type=str,
                        help="Path to input directory (contains 'results').")
                        
    parser.add_argument("-j", "--check_json", action='store_true', default=False,
                        help="Check if the jsons are non empty")
                        
    main(**parser.parse_args().__dict__)
        
        
        
