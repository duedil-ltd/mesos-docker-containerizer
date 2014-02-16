#!/usr/bin/env python

#      _            _                  _                        _
#   __| | ___   ___| | _____ _ __     | | __ _ _   _ _ __   ___| |__   ___ _ __
#  / _` |/ _ \ / __| |/ / _ \ '__|____| |/ _` | | | | '_ \ / __| '_ \ / _ \ '__|
# | (_| | (_) | (__|   <  __/ | |_____| | (_| | |_| | | | | (__| | | |  __/ |
#  \__,_|\___/ \___|_|\_\___|_|       |_|\__,_|\__,_|_| |_|\___|_| |_|\___|_|
#
#  CLI tool for launching an instance of a docker container on a Mesos cluster.
#


import argparse
import sys

import mesos
import mesos_pb2


class ContainerScheduler(mesos.Scheduler):
    """Mesos Scheduler implementation for launching a single docker container
    onto a mesos cluster."""

    def __init__(self, image, invoke, cpu=1.0, mem=32, docker_arguments=None):

        self.image = image
        self.invoke = invoke
        self.cpu = cpu
        self.mem = mem
        self.docker_arguments = docker_arguments

        self.launched = False

    def registered(self, driver, frameworkId, masterInfo):

        print >> sys.stderr, "Registered framework"

    def resourceOffers(self, driver, offers):

        if self.launched:
            return

        print >> sys.stderr, "Offered resources"

        for offer in offers:
            offer_cpu = 0.0
            offer_mem = 0

            for resource in offer.resources:
                if resource.name == "cpus":
                    offer_cpu = resource.scalar
                if resource.name == "mem":
                    offer_mem = resource.scalar

            if offer_cpu >= self.cpu and offer_mem >= self.mem:
                print >> sys.stderr, "Launching task"
                self._launchContainerTask(offer, driver)
            else:
                print >> sys.stderr, "Resource offer too small"

    def statusUpdate(self, driver, update):

        print >> sys.stderr, "Received task status update"

        terminal = False

        if update.state == mesos_pb2.TASK_FAILED:
            print >> sys.stderr, "Container task failed"
            driver.killTask(update.task_id)
            terminal = True
        elif update.state == mesos_pb2.TASK_FINISHED:
            print >> sys.stderr, "Container task finished successfully"
            terminal = True
        elif update.state == mesos_pb2.TASK_KILLED:
            print >> sys.stderr, "Container task killed"
            driver.killTask(update.task_id)
            terminal = True
        elif update.state == mesos_pb2.TASK_LOST:
            print >> sys.stderr, "Container task lost"
            driver.killTask(update.task_id)
            terminal = True

        if terminal:
            driver.stop()

    def _launchContainerTask(self, offer, driver):

        task = mesos_pb2.TaskInfo()
        task.name = "docker_container"
        task.task_id.value = "main"
        task.slave_id.value = offer.slave_id.value

        # Define the command
        task.command.value = " ".join(self.invoke)
        task.command.container.image = self.image
        if self.docker_arguments:
            task.command.container.options = self.docker_arguments

        # Build up the resources
        cpu_resource = task.resources.add()
        cpu_resource.name = "cpus"
        cpu_resource.type = mesos_pb2.Value.SCALAR
        cpu_resource.scalar.value = self.cpu

        mem_resource = task.resources.add()
        mem_resource.name = "mem"
        mem_resource.type = mesos_pb2.Value.SCALAR
        mem_resource.scalar.value = self.mem

        driver.launchTasks(offer.id, [task])

        self.launched = True


def main(args):

    framework = mesos_pb2.FrameworkInfo()
    framework.user = ""  # Mesos can select the user
    framework.name = "Docker Launcher (%s)" % (args.image)

    driver = mesos.MesosSchedulerDriver(
        ContainerScheduler(
            image=args.image,
            invoke=args.invoke,
            cpu=args.cpu,
            mem=args.mem
        ),
        framework,
        args.master
    )

    status = 0
    if driver.run() == mesos_pb2.DRIVER_STOPPED:
        status = 1

    driver.stop()
    return status


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="docker-launcher")
    parser.add_argument("-m", "--master", required=True, type=str,
                        help="IP/Port of mesos master")
    parser.add_argument("-i", "--image", required=True,
                        help="Docker image to launch the container")
    parser.add_argument("-d", "--docker_arguments", required=False,
                        help="Custom arguments to pass to docker")
    parser.add_argument("--cpu", type=float, default=1.0,
                        help="CPU Requirement")
    parser.add_argument("--mem", type=int, default=1.0,
                        help="Memory requirement (Megabytes)")
    parser.add_argument("invoke", nargs="*",
                        help="Command line invocation for the container")

    exit(main(parser.parse_args()))
