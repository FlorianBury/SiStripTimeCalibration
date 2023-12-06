## compare_2_files.py
## 6.12.23
## compare two files, line by line and find where there are inequalities...

from argparse import ArgumentParser
import os
from tqdm import tqdm

def get_file_content(file_path):
    with open(f"{file_path}", "r") as file:
        file_content = file.readlines()
        return file_content
        
def line_by_line(smaller_file, larger_file, verbose):
    ''' compare line by line if equal contents or not '''
    differences = {}
    matching = 0
    for i, (s_small, s_large) in tqdm(enumerate(zip(smaller_file, larger_file))):
        if s_small == s_large:
            matching += 1
            continue
        if verbose:
            print(f"Line: {i+1}")
            print(f" - small: {s_small}")
            print(f" - large: {s_large}")
        differences[str(i+1)] = {'small':s_small, 'large':s_large}
    
    print(f"Matching lines: {(matching/len(smaller_file))*100}%")
    print(f"Number of different lines: {len(differences.keys())}")
    return differences
            
def file_comparison(file_1, file_2, verbose):
    ''' check where two files differ '''
    file_1_content = get_file_content(file_1)
    file_2_content = get_file_content(file_2)
    
    # first comparison = lengths
    file_1_len = len(file_1_content)
    file_2_len = len(file_2_content)
    print(f"File lengths: {file_1_len, file_2_len}")
    
    # so we can give ratio at end as func. of smaller file
    smaller_file = {'content':file_1_content,'path':file_1}
    larger_file = {'content':file_2_content,'path':file_2}
    if file_2_len < file_1_len:
        smaller_file = {'content':file_2_content,'path':file_2}
        larger_file = {'content':file_1_content,'path':file_1}
        
    print(f"Small: {smaller_file['path']}")
    print(f"Large: {larger_file['path']}")
        
    # check line by line
    line_differences = line_by_line(smaller_file['content'], larger_file['content'], verbose)
    
    return line_differences
    
def main(file_1, file_2, verbose):
    
    print("-"*20)
    print(f"Comparing files, line by line")
    print(f"File 1: {file_1}")
    print(f"File 2: {file_2}")
    print(f"Verbose: {verbose}")
    
    file_comparison(file_1, file_2, verbose)
        
    print(f"Done")
    print("-"*20)

if __name__ == '__main__':
    
    parser = ArgumentParser()

    parser.add_argument("-f1", "--file_1", type=str,
                        help="Path to file 1.")
    
    parser.add_argument("-f2", "--file_2", type=str,
                        help="Path to file 2.")

    parser.add_argument("-v", "--verbose", action='store_true', default=False,
                        help="Print out per-line comparison.")
                        
    main(**parser.parse_args().__dict__)



    
