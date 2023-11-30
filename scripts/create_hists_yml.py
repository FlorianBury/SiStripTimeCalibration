## create_hists_yml.py
## 28.11.23
## is gonna take forever to create a hists yml file for a given range, so automate it

import yaml
import numpy as np
from argparse import ArgumentParser

def delay_to_string(delay):
    ''' format delay from 0.1 to XpY0000 formatting '''
    
    # if 0.1, --> 0p100000 where 6 = n. sig figs to add after p
    granularity = 6
    joiner = 'p'
    granularity=6
    joiner='p'
    
    str_delay = str(delay)
    str_delay = str_delay.split('.')
    add_zeros = granularity - len(str_delay[-1])
    str_delay = joiner.join(str_delay)
    str_delay = str_delay + (str(0)*add_zeros)
    return str_delay
    
def create_dict(start_delay, end_delay, step, module_2S_PS):
    ''' create dict to be used in yaml file '''
    delays = np.arange(start_delay, end_delay+step, step)
    
    yaml_dict = {}
    
    bxhist_1d_dir = "DQMData/Run 1/Ph2TkBXHist/Run summary/Hist1D"
    
    for delay in delays:
    
        delay = float(round(delay,1))
        str_delay = delay_to_string(delay)
        
        delay_dict = {'delay':delay, 'dir':bxhist_1d_dir}
        
        if module_2S_PS == 'both':
            name_delay = f"BXHistogram{{mode}}Offset{str_delay}"
        else:
            name_delay = f"BXHistogram{{mode}}Offset_{module_2S_PS}{str_delay}"
        yaml_dict[name_delay] = delay_dict
        
    return yaml_dict
        
def create_yaml(yaml_dict, output_file):
    ''' create the yaml file '''
    with open(output_file, 'w') as file:
        yaml.dump(yaml_dict, file, default_flow_style=False)
    
def main(output_dir, output_name, start_delay, end_delay, step, module_2S_PS):

    print("-"*20)
    print(f"Automatically creating hists.yml file")
    print(f"Output directory: {output_dir}")
    print(f"Output name: {output_name}")
    print(f"Start delay: {start_delay} (ns)")
    print(f"End delay: {end_delay} (ns)")
    print(f"Step: {step} (ns)")
    print(f"Module: {module_2S_PS}")
    
    yaml_dict = create_dict(start_delay, end_delay, step, module_2S_PS)
    create_yaml(yaml_dict, f"{output_dir}/{output_name}")
    
    print(f"Done")
    print("-"*20)
    
if __name__ == '__main__':
    
    parser = ArgumentParser()
    
    parser.add_argument("-od", "--output_dir", type=str,
                    help="Output directory to save file to.")
    
    parser.add_argument("-on", "--output_name", type=str, default="hists.yml",
                        help="Name of file (default = hists.yml).")

    parser.add_argument("-start", "--start_delay", type=float, default=0.,
                        help="Starting offset delay value (ns)")
                        
    parser.add_argument("-end", "--end_delay", type=float, default=50.,
                    help="Ending delay value (ns)")
                    
    parser.add_argument("-step", "--step", type=float, default=0.1,
                    help="Step size between delays (ns)")
                    
    parser.add_argument("-mod", "--module_2S_PS", type=str, default='both', choices=['2S','PS','both'],
                    help="Which module to specify (or not 'both')")
                        
    main(**parser.parse_args().__dict__)
    
    
    
