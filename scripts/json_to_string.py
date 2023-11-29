## json_to_string.py
## 29.11.23
## script to convert all json input to string (temp fix for thresholdScan)

import glob
import json
from argparse import ArgumentParser
from tqdm import tqdm

def get_json_files(directory):
    ''' need path to results directory '''
    file_list = glob.glob(f"{directory}/*/*.json")
    return file_list
    
def modify_file(file_path, verbose):
    ''' recreate json files with all parameters as strings '''
    
    if verbose: print(f"File path: {file_path}")
    with open(file_path, 'r') as og_file:
        content = json.load(og_file)
    
    if verbose: print(f"- Got content")
    content = {k:str(v) for k, v in content.items()}
    if verbose: print(f"- Processed content")
    
    with open(file_path, 'w') as new_file:
        json.dump(content, new_file)
    
    if verbose: print(f"- Created new file")
        
def main(input_directory, num_files, verbose):

    print("-"*20)
    print(f"Converting all json parameters to string")
    print(f"Input directory: {input_directory}")
    
    json_files = get_json_files(input_directory)
    
    for f_path in tqdm(json_files[0:num_files]):
        modify_file(f_path, verbose)
    
    print(f"Done")
    print("-"*20)

if __name__ == '__main__':
    
    parser = ArgumentParser()

    parser.add_argument("-i", "--input_directory", type=str, default=".",
                        help="Path to results directory.")
                        
    parser.add_argument("-n", "--num_files", type=int, default=None,
                        help="Number of files to process.")
                        
    parser.add_argument("-v", "--verbose", action='store_true', default=False,
                        help="Verbosity in output.")

    main(**parser.parse_args().__dict__)
