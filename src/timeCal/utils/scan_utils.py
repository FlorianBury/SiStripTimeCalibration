import numpy as np
import itertools

def makeScan(paramDict):
    # Make sure each value is a list #
    pNames = []
    pValues = []
    for pName in sorted(paramDict.keys()):
        pNames.append(pName)
        pValue = paramDict[pName]
        if not isinstance(pValue,(list,tuple,np.ndarray)):
            pValue = [pValue]
        pValues.append(pValue)

    # Make combinations #
    pCombs = []
    for prod in itertools.product(*pValues):
        pComb = []
        for p in prod:
            if isinstance(p,float):
                p = round(p,10) # Truncation of 0.000..00x problems
            pComb.append(str(p))
        pCombs.append(pComb)
    return pNames,pCombs


