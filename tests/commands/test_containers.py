from StringIO import StringIO
from unittest import TestCase

from containerizer.commands.containers import parse_docker_ps


class RunningContainersTestCase(TestCase):

    def test_running_containers(self):

        docker_ps = StringIO()
        docker_ps.write(
            "CONTAINER ID    IMAGE    COMMAND    CREATED    STATUS    PORTS    NAMES\n"  # Header record
            "XXXXXXXXXXXX    XXXXX    XXXXXXX    XXXXXXX    XXXXXX             foobar\n"
            "YYYYYYYYYYYY    YYYYY    YYYYYYY    YYYYYYY    YYYYYY             bazwin\n"
        )

        docker_ps.seek(0)  # Seek the StringIO back to the beginning
        running_containers = parse_docker_ps(docker_ps)

        self.assertEqual(len(running_containers.containers), 2)
        self.assertEqual(running_containers.containers[0].value, "foobar")
        self.assertEqual(running_containers.containers[1].value, "bazwin")
