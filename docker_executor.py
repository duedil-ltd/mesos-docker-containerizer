#!/usr/bin/env python

#      _            _                                           _
#   __| | ___   ___| | _____ _ __       _____  _____  ___ _   _| |_ ___  _ __
#  / _` |/ _ \ / __| |/ / _ \ '__|____ / _ \ \/ / _ \/ __| | | | __/ _ \| '__|
# | (_| | (_) | (__|   <  __/ | |_____|  __/>  <  __/ (__| |_| | || (_) | |
#  \__,_|\___/ \___|_|\_\___|_|        \___/_/\_\___|\___|\__,_|\__\___/|_|
#
#  Custom Mesos Executor for launching docker containers. This executor
#  implementation is designed only to run a single task. The docker invocation
#  is taken from sys.argv of _this_ python file, not the commandInfo from
#  the task.
#
#  TODO: Fix the above - Move the building of the docker invoke into a general
#  util function so it can be shared.
#

import subprocess
import threading
import sys

import mesos
import mesos_pb2


class DockerExecutor(mesos.Executor):

    def __init__(self, command):

        self.command = command

    def launchTask(self, driver, task):

        def run_task():
            print >> sys.stderr, "Launching task with command %r" % (self.command)

            proc = subprocess.Popen(self.command)

            update = mesos_pb2.TaskStatus()
            update.task_id.value = task.task_id.value
            update.state = mesos_pb2.TASK_RUNNING
            driver.sendStatusUpdate(update)

            # Wait for the process to exit
            return_code = proc.wait()

            update = mesos_pb2.TaskStatus()
            update.task_id.value = task.task_id.value
            update.state = mesos_pb2.TASK_FINISHED

            # The task failed if it exited with a non-zero exit code
            if return_code > 0:
                update.state = mesos_pb2.TASK_FAILED

            # Send the terminal update
            driver.sendStatusUpdate(update)

        thread = threading.Thread(target=run_task)
        thread.start()

    def frameworkMessage(self, driver, message):

        # Send the message back to the driver
        driver.sendFrameworkMessage(message)


if __name__ == "__main__":

    # Pull the full command to execute from the executor invoke
    command = sys.argv[1:]

    print >> sys.stderr, "Launching docker executor"

    # Launch the executor driver
    executor = DockerExecutor(command)
    driver = mesos.MesosExecutorDriver(executor)

    status = 0
    if driver.run() == mesos_pb2.DRIVER_STOPPED:
        status = 1

    driver.stop()
    exit(status)
