import os
import sys
import numpy as np
import pandas as pd
from array import array
import ROOT

__author__ = "Florian Bury"
__email__ = "florian.bury@cern.ch"

if sys.version_info.major == 2 or sys.version_info.minor < 6:
    raise RuntimeError("This script must be used with python version >= 3.6")
    # Need python3.6+ to have the dict insertion order


class Observable:
    """
        Class helper to handle the obervable array values
        Transforms the pandas DataFrame into a multi-dim numpy array with labels tracking
    """
    def __init__(self,array,labels,name=''):
        """
            Initialize
            Input  :
                - array [np.ndarray] : array of values
                - labels [dict(str:np.ndarray)] : dict of labels of the values array with names and axes values
                - name [str] (default = '') : name of the observable
        """
        self.array  = array
        self.labels = labels
        self.name   = name

    def PrintLabels(self):
        """
            Print the labels with associated values
            Input  : None
            Return : None
        """
        print ('Observable array has following labels')
        for labelName, labelTicks in self.labels.items():
            print ('Name   : "{}"'.format(labelName))
            print ('Values : \n',labelTicks)

    def GetSlice(self,**kwargs):
        """
            Selects a subset of parameters
            Input  :
                - **kwargs : either parameter values by name or dictionnary
            Return : Observable instance with reduced array
        """
        for key in kwargs.keys():
            if key not in self.labels.keys():
                raise ValueError('Could not find label "{}" in data labels : ['.format(key)+','.join(self.labels.keys())+']')
        arr_select = self.array
        labels_select = {}
        for idx,key in reversed(list(enumerate(self.labels.keys()))):
            if key in kwargs.keys():
                try:
                    element = np.where(self.labels[key]==kwargs[key])[0][0]
                except IndexError:
                    raise IndexError('Cannot find element with value {} of label "{}"'.format(kwargs[key],key))
                arr_select = arr_select.take(element,idx)
            else:
                labels_select[key] = self.labels[key]
        labels_select = {key:labels_select[key] for key in reversed(list(labels_select.keys()))}
        return Observable(arr_select,labels_select)

    def GetArray(self):
        """
            Returns the array of the instance
            Input  : None
            Return : np.ndarray of the data values
        """
        return self.array

    def GetLabels(self):
        """
            Returns the labels of the instance
            Input  : None
            Return : dict(str:np.ndarray) of labels and values
        """
        return self.labels

    @staticmethod
    def _getEdgesFromCenters(x):
        """
            Helper method to get the centers from the bin edges
            Note : Assumes bin edge is the mediam between two centers
                -> In case of different bin widths, the center will not be in the "bin center"
            Input  :
                - x [np.ndarray] : bin edges
            Return : centers of the bins [np.ndarray]
        """
        d = np.diff(x)/2
        return np.r_[x[0]-d[0],x[0]+d[0],x[1:-1]+d[1:],x[-1]+d[-1]]
        #return np.concatenate(((x[:-1] - np.diff(x)/2)[:2],x[1:] + np.diff(x)/2))


    #######################################
    #              1D Plots               #
    #######################################
    def _get1DScan(self):
        """
            Get 1D scan values
            Input  : None
            Return : (xvalues[np.ndarray],yvalues[np.ndarray])
        """
        if len(self.array.shape) != 1:
            raise RuntimeError('Current array is dimention {}, to build a TGraph scan you need to have a dimension 1 array, maybe you need to slice the obervable array'.format(len(self.array.shape)))
        xvalues = list(self.labels.values())[0]
        yvalues = self.array
        return xvalues,yvalues

    def GetRootTH1(self,name=''):
        """
            Return TH1 scan of single parameter observable
            Input  :
                - name [str] (default = '') : name to give the TH1
            Return : ROOT.TH1 of the scan
        """
        xval,yval = self._get1DScan()
        xedges = self._getEdgesFromCenters(xval)
        xlabel = list(self.labels.keys())[0]
        h = ROOT.TH1F(name,name,
                      xedges.shape[0]-1, array('d',xedges))
        for ix in range(xedges.shape[0]-1):
            h.SetBinContent(ix+1,yval[ix])
        h.GetXaxis().SetTitle(xlabel)
        h.GetYaxis().SetTitle(self.name)
        return h

    def GetRootTGraph(self,name=''):
        """
            Return TGraph scan of single parameter observable
            Input  :
                - name [str] (default = '') : name to give the TH1
            Return : ROOT.TGraph of the scan
        """
        xval,yval = self._get1DScan()
        g = ROOT.TGraph(xval.shape[0],xval,yval)
        xlabel = list(self.labels.keys())[0]
        g.GetXaxis().SetTitle(xlabel)
        g.GetYaxis().SetTitle(self.name)
        g.SetName(name)
        return g

    def Pyplot1D(self,ax,**kwargs):
        """
            Adds the 1D plot to a matplotlib.pyplot subplot
            Input  :
                - ax [subplot instance] : the subplot on which to add the curve
                - kwargs : all the options one cas use in pyplot.plot()
            Return : None
        """
        xval,yval = self._get1DScan()
        ax.plot(xval,yval,**kwargs)

    #######################################
    #              2D Plots               #
    #######################################
    def _get2DScan(self,x,y):
        """
            Get 2D scan values
            Input  :
                - x [str] : label in the x axis
                - y [str] : label in the y axis
            Return : (xvalues[np.ndarray],yvalues[np.ndarray],values[np.ndarray])
        """
        if len(self.array.shape) != 2:
            raise RuntimeError('Current array is dimention {}, to build a TH2 you need to have a dimension 2 array, maybe you need to slice the obervable array'.format(len(self.array.shape)))
        if x not in self.labels.keys():
            raise RuntimeError("X axis label {} not found in observable labels (check with PrintLabels())")
        if y not in self.labels.keys():
            raise RuntimeError("Y axis label {} not found in observable labels (check with PrintLabels())")

        xpos = list(self.labels).index(x)
        ypos = list(self.labels).index(y)
        xvalues = self.labels[x]
        yvalues = self.labels[y]
        values = self.array.transpose(xpos,ypos)

        return xvalues,yvalues,values


    def GetRootTH2(self,x,y,name=''):
        """
            Return TH2 scan of two parameters observable
            Input  :
                - x [str] : label in the x axis
                - y [str] : label in the y axis
                - name [str] (default = '') : name to give the TH2
            Return : ROOT.TH2 of the scan
        """
        xval,yval,values = self._get2DScan(x,y)
        xedges = self._getEdgesFromCenters(xval)
        yedges = self._getEdgesFromCenters(yval)
        h = ROOT.TH2F(name,name,
                      xedges.shape[0]-1, array('d',xedges),
                      yedges.shape[0]-1, array('d',yedges))

        for ix in range(xedges.shape[0]-1):
            for iy in range(yedges.shape[0]-1):
                h.SetBinContent(ix+1,iy+1,values[ix,iy])
        h.GetXaxis().SetTitle(x)
        h.GetYaxis().SetTitle(y)
        h.GetZaxis().SetTitle(self.name)

        return h

    def GetRootTGraph2D(self,x,y,name=''):
        """
            Return TGraph2D scan of two parameters observable
            Input  :
                - x [str] : label in the x axis
                - y [str] : label in the y axis
                - name [str] (default = '') : name to give the TGraph2D
            Return : ROOT.TGraph2D of the scan
        """
        xval,yval,values = self._get2DScan(x,y)
        X,Y = np.meshgrid(xval,yval,indexing='ij')
        X = X.ravel().astype(np.float32)
        Y = Y.ravel().astype(np.float32)
        Z = values.ravel().astype(np.float32)
        print (X.dtype,Y.dtype,Z.dtype)
        g = ROOT.TGraph2D(Z.shape[0],X,Y,Z)
        g.GetXaxis().SetTitle(x)
        g.GetYaxis().SetTitle(y)
        g.SetName(name)
        return ROOT.TGraph2D(self.GetRootTH2(x,y,name))

    def Pyplot2D(self,x,y,ax,**kwargs):
        """
            Adds the 2D plot to a matplotlib.pyplot subplot
            Input  :
                - x [str] : label in the x axis
                - y [str] : label in the y axis
                - ax [subplot instance] : the subplot on which to add the curve
                - kwargs : all the options one cas use in pyplot.pcolormesh()
            Return : the pcolormesh instance, eg to be used for a colorbar
        """
        xval,yval,values = self._get2DScan(x,y)
        X,Y = np.meshgrid(xval,yval,indexing='ij')
        return ax.pcolormesh(X,Y,values,**kwargs)

    #######################################
    #              3D Plots               #
    #######################################
    def _get3DScan(self,x,y,z):
        """
            Get 2D scan values
            Input  :
                - x [str] : label in the x axis
                - y [str] : label in the y axis
                - z [str] : label in the z axis
            Return : (xvalues[np.ndarray],yvalues[np.ndarray],zvalues[np.ndarray],values[np.ndarray])
        """
        if len(self.array.shape) != 3:
            raise RuntimeError('Current array is dimention {}, to build a TH3 you need to have a dimension 3 array, maybe you need to slice the obervable array'.format(len(self.array.shape)))
        if x not in self.labels.keys():
            raise RuntimeError("X axis label {} not found in observable labels (check with PrintLabels())")
        if y not in self.labels.keys():
            raise RuntimeError("Y axis label {} not found in observable labels (check with PrintLabels())")
        if z not in self.labels.keys():
            raise RuntimeError("Z axis label {} not found in observable labels (check with PrintLabels())")


        xpos = list(self.labels).index(x)
        ypos = list(self.labels).index(y)
        zpos = list(self.labels).index(z)
        xvalues = self.labels[x]
        yvalues = self.labels[y]
        zvalues = self.labels[z]
        values = self.array.transpose(xpos,ypos,zpos)

        return xvalues,yvalues,zvalues,values

    def GetRootTH3(self,x,y,z,name=''):
        """
            Return TH3 scan of two parameters observable
            Input  :
                - x [str] : label in the x axis
                - y [str] : label in the y axis
                - z [str] : label in the z axis
                - name [str] (default = '') : name to give the TH3
            Return : ROOT.TH3 of the scan
        """
        xval,yval,zval,values = self._get3DScan(x,y,z)
        xedges = self._getEdgesFromCenters(xval)
        yedges = self._getEdgesFromCenters(yval)
        zedges = self._getEdgesFromCenters(zval)
        h = ROOT.TH3F(name,name,
                      xedges.shape[0]-1, array('d',xedges),
                      yedges.shape[0]-1, array('d',yedges),
                      zedges.shape[0]-1, array('d',zedges))

        for ix in range(xedges.shape[0]-1):
            for iy in range(yedges.shape[0]-1):
                for iz in range(zedges.shape[0]-1):
                    h.SetBinContent(ix+1,iy+1,iz+1,values[ix,iy,iz])
        h.GetXaxis().SetTitle(x)
        h.GetYaxis().SetTitle(y)
        h.GetZaxis().SetTitle(z)
        h.SetTitle(self.name)

        return h




class Data:
    """
        Class helper to extract information from the pandas DataFrame
    """
    def __init__(self,df):
        """
            Initialize with a pandas DataFrame
            Input  :
                - df [pd.DataFrame] : dataframe of data values
            Return : None
        """
        self.df = df
        self.parameters = self.df.columns

    def SetParameters(self,parameters):
        """
            Define the parameters for the scans
            Inputs :
                - parameters [list(str)] : list of strings of parameter names
            Return : None
        """
        assert isinstance(parameters,list)
        for param in parameters:
            if param not in self.df.columns:
                raise RuntimeError('Parameter "{}" not found in the dataframe'.format(param))
        self.parameters = parameters

    def ListNames(self):
        """
            Prints the list of columns in the dataframe
            Inputs : None
            Return : None
        """
        print ("The columns in the dataframe are")
        for col in sorted(self.df.columns):
            print ('... {}'.format(col))

    def GetObservable(self,observable):
        """
            Select one observable from the DF columns and produce an Obervable instance
            Input  :
                - observable [str] : name of the observable from the dataframe columns
            Return : Observable instance
        """
        if observable not in self.df.columns:
            raise RuntimeError('Observable "{}" not found in the dataframe'.format(observable))

        axNames = self.parameters
        df = self.df[axNames+[observable]]
        grouped = df.groupby(axNames)[observable].mean()
        shape = tuple(map(len, grouped.index.levels))
        arr = np.full(shape, np.nan)
        arr[tuple(grouped.index.codes)] = grouped.values.flat
        labels = {level.name:level.values for level in grouped.index.levels}
        return Observable(arr,labels,observable)

    @classmethod
    def load_pickle(cls,path):
        """
            Instantiate the Data class from a pickle file
            Input  :
                - path [str] : string of the path to the pickle dataframe file
            Return : Data instance
        """
        if not os.path.exists(path):
            raise
        df = pd.read_pickle(path)
        return cls(df)

