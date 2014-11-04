from unittest import TestCase
from mock import patch

from containerizer.commands.launch import build_docker_args
from containerizer.proto import Launch


@patch.dict("os.environ", {
    "MESOS_LIBEXEC_DIRECTORY": "/bin",
    "MESOS_DEFAULT_CONTAINER_IMAGE": "default/container"
})
@patch("containerizer.commands.launch.fetch_uris", return_value=0)
@patch("containerizer.commands.launch.invoke_docker", return_value=(None, None, 0))
class LaunchContainerTestCase(TestCase):

    def test_launch_container_task_info_default(self, _, __):

        launch = Launch()
        launch.container_id.value = "container-foo-bar"
        launch.directory = "/tmp"
        launch.user = "test"

        self.assertEqual(build_docker_args(launch), [
            "-d",
            "--name", "container-foo-bar",
            "--net", "host",
            "-u", "test",
            "-e", "MESOS_DIRECTORY=/mesos-sandbox",
            "-v", "/tmp:/mesos-sandbox",
            "-w", "/mesos-sandbox",
            "default/container",
            "sh", "-c",
            "/bin/mesos-executor >> /mesos-sandbox/docker_stdout 2>> /mesos-sandbox/docker_stderr"
        ])

    def test_launch_container_task_info_resources(self, _, __):

        launch = Launch()
        launch.container_id.value = "container-foo-bar"
        launch.directory = "/tmp"
        launch.user = "test"

        cpu_resource = launch.task_info.resources.add()
        cpu_resource.name = "cpus"
        cpu_resource.type = 0
        cpu_resource.scalar.value = 1

        mem_resource = launch.task_info.resources.add()
        mem_resource.name = "mem"
        mem_resource.type = 0
        mem_resource.scalar.value = 1024

        port_resource = launch.task_info.resources.add()
        port_resource.name = "ports"
        port_resource.type = 1

        port = port_resource.ranges.range.add()
        port.begin = 2234
        port.end = 2234

        port = port_resource.ranges.range.add()
        port.begin = 4400
        port.end = 4401

        self.assertEqual(build_docker_args(launch), [
            "-d",
            "--name", "container-foo-bar",
            "--net", "host",
            "-u", "test",
            "-c", "256",
            "-m", "1024m",
            "-p", ":4400",
            "-p", ":4401",
            "-p", ":2234",
            "-e", "MESOS_DIRECTORY=/mesos-sandbox",
            "-v", "/tmp:/mesos-sandbox",
            "-w", "/mesos-sandbox",
            "default/container",
            "sh", "-c",
            "/bin/mesos-executor >> /mesos-sandbox/docker_stdout 2>> /mesos-sandbox/docker_stderr"
        ])

    def test_launch_container_task_info_container_info(self, _, __):

        launch = Launch()
        launch.container_id.value = "container-foo-bar"
        launch.directory = "/tmp"
        launch.user = "test"

        launch.task_info.container.type = 1  # DOCKER
        launch.task_info.container.docker.image = "custom/image"
        launch.task_info.container.docker.network = 2

        self.assertEqual(build_docker_args(launch), [
            "-d",
            "--name", "container-foo-bar",
            "--net", "bridge",
            "-u", "test",
            "-e", "MESOS_DIRECTORY=/mesos-sandbox",
            "-v", "/tmp:/mesos-sandbox",
            "-w", "/mesos-sandbox",
            "custom/image",
            "sh", "-c",
            "/bin/mesos-executor >> /mesos-sandbox/docker_stdout 2>> /mesos-sandbox/docker_stderr"
        ])

    def test_launch_container_task_info_container_info_bad_ports(self, _, __):

        launch = Launch()
        launch.container_id.value = "container-foo-bar"
        launch.directory = "/tmp"
        launch.user = "test"

        launch.task_info.container.type = 1  # DOCKER
        launch.task_info.container.docker.image = "custom/image"
        launch.task_info.container.docker.network = 2

        port = launch.task_info.container.docker.port_mappings.add()
        port.host_port = 1234
        port.container_port = 4567

        with self.assertRaises(Exception):
            self.assertEqual(build_docker_args(launch), [
                "-d",
                "--name", "container-foo-bar",
                "--net", "bridge",
                "-u", "test",
                "-e", "MESOS_DIRECTORY=/mesos-sandbox",
                "-v", "/tmp:/mesos-sandbox",
                "-w", "/mesos-sandbox",
                "custom/image",
                "sh", "-c",
                "/bin/mesos-executor >> /mesos-sandbox/docker_stdout 2>> /mesos-sandbox/docker_stderr"
            ])

    def test_launch_container_task_info_container_info_port_map(self, _, __):

        launch = Launch()
        launch.container_id.value = "container-foo-bar"
        launch.directory = "/tmp"
        launch.user = "test"

        port_resource = launch.task_info.resources.add()
        port_resource.name = "ports"
        port_resource.type = 1

        port = port_resource.ranges.range.add()
        port.begin = 1234
        port.end = 1235

        launch.task_info.container.type = 1  # DOCKER
        launch.task_info.container.docker.image = "custom/image"
        launch.task_info.container.docker.network = 2

        port = launch.task_info.container.docker.port_mappings.add()
        port.host_port = 1234
        port.container_port = 9001

        port = launch.task_info.container.docker.port_mappings.add()
        port.host_port = 1235
        port.container_port = 9002
        port.protocol = "udp"

        self.assertEqual(build_docker_args(launch), [
            "-d",
            "--name", "container-foo-bar",
            "--net", "bridge",
            "-u", "test",
            "-p", ":1234",
            "-p", ":1235",
            "-e", "MESOS_DIRECTORY=/mesos-sandbox",
            "-v", "/tmp:/mesos-sandbox",
            "-w", "/mesos-sandbox",
            "-p", "1234:9001",
            "-p", "1235:9002/udp",
            "custom/image",
            "sh", "-c",
            "/bin/mesos-executor >> /mesos-sandbox/docker_stdout 2>> /mesos-sandbox/docker_stderr"
        ])
