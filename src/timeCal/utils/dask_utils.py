import sys
import time
import dask
import dask.distributed
from IPython import embed
from collections import defaultdict
import signal

ORDER_STATUS = ['stored','pending','running','finished','cancelled','error','lost','cleaned']

class MonitoringLoop:
    def __init__(self,futures,client,cluster,logger,interval=60):
        self.futures = futures
        self.client = client
        self.cluster = cluster
        self.logger = logger
        self.interval = interval
        self.statuses = defaultdict(lambda: 0)

    def close(self,exit=False):
        self.logger.info('Shutting down cluster and client')
        self.cluster.close()
        self.client.close()
        if exit:
            self.logger.info('Exiting program')
            sys.exit(1)

    def retry(self):
        for future in self.futures:
            future.retry()

    def cancel(self):
        for future in self.futures:
            future.cancel()

    def updateStatus(self):
        self.statuses.clear()
        for future in self.futures:
            self.statuses[future.status] += 1

    def countFinished(self):
        return len([future for future in self.futures if (future.status == 'finished' or future.status == 'cleaned')])

    def checkFinished(self):
        return self.countFinished() == len(self.futures)

    def countRemaining(self):
        return len([future for future in self.futures if (future.status == 'pending' or future.status == 'running')])

    def checkRemaining(self):
        return self.countRemaining() > 0

    def printStatusInfo(self):
        if len(set(self.statuses.keys()) - set(ORDER_STATUS)) > 0:
            raise RuntimeError(f'Unknown {set(self.statuses.keys()) - set(ORDER_STATUS)} dask statuses, this should not happen')
        self.logger.info('Current status :')
        for status in ORDER_STATUS:
            if self.statuses[status] > 0:
                self.logger.info(f'\t- {self.statuses[status]:5d} {status:15s} [{self.statuses[status]/len(self.futures)*100:6.2f}%]')

    def printClusterInfo(self):
        local = isinstance(self.cluster, dask.distributed.LocalCluster)
        self.logger.info(f'Cluster {self.cluster.status._value_} at {self.cluster.dashboard_link} : ')
        self.logger.info(f'\t- {len(self.cluster.workers):5d} workers')
        self.logger.info(f'\t- {sum(self.client.nthreads().values()):5d} threads')
        self.logger.info(f'\t- {sum(self.client.ncores().values()):5d} cores')
        if local:
            self.logger.info(f'\t- {sum([worker.memory_manager.memory_limit for worker in self.cluster.workers.values()])/1024**3:5.0f} GiB of memory limit')
        else:
            self.logger.info(f'\t- {sum([worker.worker_memory for worker in self.cluster.workers.values()])/1024**3:5.0f} GiB of memory')
        if len(self.cluster.workers) > 0:
            self.logger.debug('Current workers info are listed below :')
        if self.logger.level  == 'debug':
            # If not debug mode, no need to process those lines
            for workerName, workerObj in self.cluster.workers.items():
                self.logger.debug(f'... Worker {workerName}')
                self.logger.debug(f'    Name             : {workerObj.name}')
                if local:
                    self.logger.debug(f'    Memory limit[GB] : {workerObj.memory_manager.memory_limit/(1024)**3:.3f}')
                    self.logger.debug(f'    Threads          : {workerObj.nthreads}')
                else:
                    self.logger.debug(f'    Job ID           : {workerObj.job_id}')
                    self.logger.debug(f'    Memory limit[GB] : {workerObj.worker_memory/(1024)**3:.3f}')
                    self.logger.debug(f'    Cores            : {workerObj.worker_cores}')
                    self.logger.debug(f'    Processes        : {workerObj.worker_processes}')


    @property
    def user_command_info(self):
        return {
            "help"     : "print available user commands",
            "exit"     : "close the cluster and exit program",
            "status"   : "print status of jobs and cluster (on top of the monitoring loop)",
            "interval" : "change the time interval of the monitoring loop",
            "retry"    : "to retry every failed or cancelled job",
            "cancel"   : "to cancel all the running and pending jobs",
            "client"   : "to start an interactive shell to inspect the dask client",
            "cluster"  : "to start an interactive shell to inspect the dask cluster",
            "futures"  : "to start an interactive shell to inspect the futures",
            "verbose"  : "to switch between info and debug mode of the self.logger",
            "debug"    : "",
        }

    @property
    def user_commands(self):
        return list(self.user_command_info.keys())

    @property
    def user_message(self):
        return "If you want to modify the running parameters, type any of the following commands :\n" + \
            '\n'.join([f"{command:15s} : {info}" for command,info in self.user_command_info.items()])

    @staticmethod
    def inspect_client(client):
        print ("You have here access to the `client` variable and are free to modify it as you wish\nFor example `client.has_what()` or `client.who_has()`\nTo go back to the monitoring loop, either type `exit` or hit CTRL+D")
        embed()

    @staticmethod
    def inspect_cluster(cluster):
        print ("You have here access to the `cluster` variable and are free to modify it as you wish\nFor example `cluster.scale(<number-of-jobs>)` or `cluster.adapt(<min>,<max>,**kwargs)`\nTo go back to the monitoring loop, either type `exit` or hit CTRL+D")
        embed()

    @staticmethod
    def inspect_futures(futures):
        print ("You have here access to the `futures` variable and are free to modify it as you wish\nFor example to manually check the traceback of some jobs, or inspect them in more details\nTo go back to the monitoring loop, either type `exit` or hit CTRL+D")
        embed()

    def orient_user(self,command):
        if command == 'help':
            print (self.user_message)
        if command == 'exit':
            self.close(True)
        if command == 'status':
            self.updateStatus()
            self.printStatusInfo()
            self.printClusterInfo()
        if command == 'interval':
            self.logger.info(f'Current time interval is {self.interval}s')
            answer = input(f'Enter new value for monitoring interval (in seconds)\n>>> ').strip()
            if not answer.isdigit():
                self.logger.warning(f'`{answer}` is not an integer, will dismiss it')
            else:
                self.interval = int(answer)
        if command == 'retry':
            self.retry()
        if command == 'cancel':
            self.cancel()
        if command == 'client':
            self.inspect_client(self.client)
        if command == 'cluster':
            self.inspect_cluster(self.cluster)
        if command == 'futures':
                self.inspect_futures(self.futures)
        if command == 'verbose':
            if self.logger.level == 'info':
                self.logger.info('Changing logger level : INFO -> DEBUG')
                self.logger.setLevel('debug')
            elif self.logger.level == 'debug':
                self.logger.info('Changing logger level : DEBUG -> INFO')
                self.logger.setLevel('info')
            else:
                raise ValueError
        if command == 'debug':
            embed()


    def start(self,wait=None):
        # Check if finished #
        self.updateStatus()
        if self.checkFinished():
            print (f'All jobs are already finished')
            return

        if wait is not None:
            time.sleep(wait)

        # Signal to stop user input loop #
        class EndofWaitException(Exception):
            pass
        def exitLoop(signum,frame):
            raise EndofWaitException

        # Start loop #
        self.updateStatus()
        self.printStatusInfo()
        self.printClusterInfo()
        while not self.checkFinished():
            # Start user open window of modifications #
            signal.alarm(self.interval)
            try:
                while True:
                    answer = input('>>> ').strip()
                    if len(answer) == 0:
                        continue
                    if answer in self.user_commands:
                        signal.alarm(0) # stop the check loop and do what the user asked
                        self.orient_user(answer)
                        signal.alarm(self.interval) # reset the waiting loop
                    else:
                        self.logger.warning(f'Answer `{answer}` not available')
                        signal.alarm(self.interval) # reset the waiting loop
            except EndofWaitException:
                pass

            # If nothing still running but not finished #
            if not self.checkRemaining() and not self.checkFinished():
                self.logger.info('Not any remaining running nor pending job, yet not all have finished successfully.\nWill let you decide what to do, while still checking for success in all jobs to resume the program (type `help` for details)')
                while True:
                    self.orient_user(input('>>> '))
                    if self.checkFinished():
                        break

        self.logger.info('All jobs finished successfully')
        self.close()

