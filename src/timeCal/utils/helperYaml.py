import os
import sys
import re
import glob
import yaml
from collections import OrderedDict
from pprint import pprint

d = {}
for path in glob.glob(os.path.join(sys.argv[1],'*.root')):
    f = os.path.basename(path)
    if 'harvested' not in f:
        continue
    t = int(re.findall(r'\d+',f)[0])
    ths = float(re.findall(r'\d+p\d+',f)[0].replace('p','.'))
    tos = float(re.findall(r'\d+p\d+',f)[1].replace('p','.'))
    print (f)
    print (t,ths,tos)
    d[f] = [t,ths,tos]

od = OrderedDict([(key,d[key]) for key in sorted(d.keys())])
pprint (od)

with open('blank.yml','w') as handle:
    yaml.dump(od,handle)

