import os
import io
import logging
import traceback
import warnings
import psutil

LOGGING_LEVEL = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}

LOGGING_MODE = [
    'console',
    'file',
    'both',
    'buffer',
]

warning_list = {
    'deprecation':  DeprecationWarning,
    'import':       ImportWarning,
    'resource':     ResourceWarning,
    'user':         UserWarning
}

error_list = {
    'attribute':    AttributeError,
    'index':        IndexError,
    'file':         FileExistsError,
    'memory':       MemoryError,
    'value':        ValueError,
}

class Logger:
    """
    Wrapper around python logging
    """
    def __init__(self,
        logName:   str='default',
        logLevel:  str='debug',
        logMode:   str='both',
        outputDir: str='.',
    ):
        # Check for mistakes #
        if logMode not in LOGGING_MODE:
            raise ValueError(f"Logging handler {output} not in {LOGGING_MODE}")

        # Check the logging directory #
        if not os.path.isdir(outputDir):
            raise RuntimeError(f'Output dir `{outputDir}` does not exist')

        # Save in the self #
        self.logName = logName
        self.logMode = logMode
        self.logLevel = logLevel
        self.outputDir = outputDir
        self.outputPath = os.path.join(self.outputDir,f'log.out')

        # create logger
        self.logger = logging.getLogger(self.logName)
        # Clear default handler #
        self.logger.handlers.clear()

        # set format
        class LoggingFormatter(logging.Formatter):
            grey = "\x1b[1;90m"
            yellow = "\x1b[1;33m"
            blue = "\x1b[1;34m"
            purple = "\x1b[1;35m"
            red = "\x1b[1;31m"
            black = "\x1b[1;40m"
            reset = "\x1b[0m"
            FORMATS = {
                logging.DEBUG:    f'%(asctime)s - {grey}%(levelname)s{reset} - %(message)s',
                logging.INFO:     f'%(asctime)s - {blue}%(levelname)s{reset} - %(message)s',
                logging.WARNING:  f'%(asctime)s - {yellow}%(levelname)s{reset} - %(message)s',
                logging.ERROR:    f'%(asctime)s - {red}%(levelname)s{reset} - %(message)s',
                logging.CRITICAL: f'%(asctime)s - {black}%(levelname)s{reset} - %(message)s',
            }
            def format(self, record):
                log_fmt = self.FORMATS.get(record.levelno)
                formatter = logging.Formatter(
                    fmt = log_fmt,
                    datefmt = '%Y-%m-%d %H:%M:%S',
                )
                return formatter.format(record)

        self.console_formatter = LoggingFormatter()
        self.file_formatter = logging.Formatter(
            fmt = '%(asctime)s - %(levelname)s - %(message)s',
            datefmt = '%Y-%m-%d %H:%M:%S',
        )

        # Make buffer #
        if self.logMode == 'buffer':
            self.buffer = io.StringIO()
        else:
            self.buffer = None

        # create handler
        if self.logMode in ['console','buffer', 'both']:
            self.addConsolehandler(self.buffer)
        if self.logMode in ['file', 'both']:
            self.addFileHandler(self.outputPath)

        # set level
        self.setLevel(logLevel)

    def __reduce__(self):
        return (self.__class__, (self.logName,self.logLevel,self.logMode,self.outputDir))

    def addConsolehandler(self,stream=None):
        handler = logging.StreamHandler(stream)
        handler.setFormatter(self.console_formatter)
        self.logger.addHandler(handler)

    def addFileHandler(self,path):
        handler = logging.FileHandler(path)
        handler.setFormatter(self.file_formatter)
        self.logger.addHandler(handler)

    def setLevel(self,level):
        if level not in LOGGING_LEVEL.keys():
            raise ValueError(f"Logging level {level} not in {LOGGING_LEVEL.keys()}")
        self.level = level
        logLevel = LOGGING_LEVEL[self.level]
        self.logger.setLevel(logLevel)
        for handler in self.logger.handlers:
            handler.setLevel(logLevel)

    def info(self,
        message:    str,
    ):
        """ Output to the standard logger "info" """
        return self.logger.info(message)

    def debug(self,
        message:    str,
    ):
        """ Output to the standard logger "debug" """
        return self.logger.debug(message)

    def warning(self,
        message:    str,
    ):
        """ Output to the standard logger "warning" """
        return self.logger.warning(message)

    def error(self,
        message:    str,
        error_type: str='value',
    ):
        """ Output to the standard logger "error" """
        formatted_lines = str(traceback.format_stack()[-1][0])
        if error_type not in error_list.keys():
            error_type = 'value'
        if self.logMode == 'file':
            self.logger.error(f"traceback: {formatted_lines}\nerror: {message}")
        self.logger.error(message)
        raise error_list[error_type](f"traceback: {formatted_lines}\nerror: {message}")

    def print_memory(self):
        self.logger.info(f'Current memory usage = {psutil.virtual_memory().total / (1024.0 **3):.3f} GB')

    def write(self,path):
        if self.logMode == 'buffer':
            with open(path,'w') as handle:
                handle.write(self.buffer.getvalue())
                self.buffer.close()
        else:
            self.logger.warning(f'`write` function cannot be used with mode {self.logMode}')
        # Clear handlers #
        self.logger.handlers.clear()


# create global logger
default_logger = Logger(
    logName = "default",
    logMode = "console",
)
