# How to read the data

The timing data is saved in a pickled pandas dataframe, one can either load the full data file with 
```python
    import pandas
    df = pd.read_pickle(path_to_pkl)
```
or use the helper documented below.

## Data content 
Timing variable : delay
Parameters scanned : 
- Threshold 
- Threshold Smearing
- ToF Smearing
Obvervables:
- Out-of-time fraction (+ statistical error)
- Mean (+ statistical error)
- Efficiency 
- Next BX contamination
- Previous BX contamination

## Software requirements
- python 3.6 or later
- numpy (used 1.19.4)
- pandas(used 0.24.2)
- pyROOT 6

## How to use the helper script

### Data class
The pkl file can be loaded in the helper with
```python
    from data_helper import Data
    data = Data.load_pickle(path_to_pkl)
```
and the parameters need to be set up with 
```python
    data.SetParameters(["Threshold","Threshold Smearing","ToF Smearing","delay"])
```
The columns content can be printed with
```python
    data.ListNames()
```

### Observable class

In order to produce scan plots, one needs to transform the dataframe in the Data class into an instance of the Observable class (wrapper around a multi dimensional numpy array with some plotting methods).
```python
    from data_helper import Observable
    observable = data.GetObservable("Efficiency")
```
To print the labels for each dimension, one can use 

```python
    observable.PrintLabels()
```
-> will print the names of labels + axes values

Skimming the n-dimensional array can be done with `GetSlice`, eg 

```python
    skimmedObservable = observable.GetSlice(**{'Threshold Smearing':500,'ToF Smearing':1})
```
In which case `skimmedObservable` will be a 2 dimensional array with `Threshold` and `delay` values.
NB : in principle the function could be called with `observable.GetSlice(Threshold=5000)` but since some observables have been defined with spaces, better put them in a dictionnary

NB bis : several skimmings can be applied in serie, `PrintLabels()` can be used to print the remaining labels and their values

#### 1D plots
When an observable instance has been skimmed to a single parameter (likely the `delay`), several methods can be used to plot the scan in either ROOT or matplotlib.pyplot.

ROOT plotting :
```python
    h = skimmedObservable.GetRootTH1()
    # h -> ROOT TH1 histogram
    g = skimmedObservable.GetRootTGraph()
    # g -> ROOT TGraph
```
matplotlib plotting :
```python
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    skimmedObservable.Pyplot1D(ax,**kwargs)
    # adds the 1D scan to the ax subplot, kwargs can be any pyplot options for `plt.plot`
    plt.show()
```

#### 2D plots
When an observable instance has been skimmed to a two parameters, plotting options below are available

ROOT plotting :
```python
    h = skimmedObservable.GetRootTH2()
    # h -> ROOT TH2 histogram
    g = skimmedObservable.GetRootTGraph2D()
    # g -> ROOT TGraph2D
```
matplotlib plotting :
```python
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    skimmedObservable.Pyplot2D(ax,**kwargs)
    # adds the 2D scan to the ax subplot, kwargs can be any pyplot options for `plt.pcolormesh`
    plt.show()
```


#### 3D plots
When an observable instance has been skimmed to a three parameters, plotting options below are available

ROOT plotting :
```python
    h = skimmedObservable.GetRootTH3()
    # h -> ROOT TH3 histogram
```

## Detailed examples 

```python
    # Snippet to plot 1D parameter scans in pyplot #
    from matplotlib import cm
    import matplotlib.pyplot as plt 
    
    # Load Data # 
    data = Data.load_pickle("data_Latched.pkl")
    data.SetParameters(["Threshold","Threshold Smearing","ToF Smearing","delay"])
    
    # Get efficiency observable #
    observable = data.GetObservable("Efficiency")

    # Select 2D threshold versus delay param scan #
    o2d = observable.GetSlice(**{'Threshold Smearing':0,'ToF Smearing':0})
    
    # Get threshold values #
    threshValues = o2d.GetLabels()['Threshold']
    
    # Scan all available treshold values and plot them in same figure #
    fig,ax = plt.subplots()
    colors = cm.jet(np.linspace(0,1,threshValues.shape[0]))
    for i in range(threshValues.shape[0]):
        o1d = o2d.GetSlice(Threshold=threshValues[i])
        o1d.Pyplot1D(ax,color=colors[i])
    fig.savefig('scan.png')
```

# Author
Florian Bury

florian.bury@cern.ch
