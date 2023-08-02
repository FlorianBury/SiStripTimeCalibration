import os
from configparser import ConfigParser

def getEnv():
    xdgCfg = os.getenv("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
    config = os.path.join(xdgCfg, "timerc")

    if not os.path.exists(config):
        raise RuntimeError(f'Config not found in {config}')

    cfgp = ConfigParser()
    cfgp.optionxform = str
    cfgp.read(config)
    cfg = dict((sName, dict(cfgp[sName])) for sName in cfgp.sections())            
    return cfg


