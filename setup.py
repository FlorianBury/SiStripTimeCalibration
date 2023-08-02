from setuptools import setup

if __name__ == '__main__':
    setup(
        entry_points = {
            'console_scripts': [
            'BXRun=timeCal.utils.BXRun:main',
            'plotScan=timeCal.PlotScan.plotScan:main',
            'runCalibration=timeCal.Calibration.runCalibration:main',
            ],
        },
        #install_requires = [
        #    'numpy',
        #    'pandas',
        #    'enlighten',
        #    'pyyaml',
        #    'ipython',
        #    'tk',
        #]
    )

