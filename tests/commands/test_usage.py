import mock
from unittest import TestCase

from containerizer.commands.usage import collect_container_stats
from containerizer.proto import ResourceStatistics


def mock_docker_ps():
    exit(1)


class ContainerStatsTestCase(TestCase):

    def test_collect_stats(self):

        stats = ResourceStatistics()

        def _metric(container_id, metric):
            if metric == "cpu.shares":
                yield (None, 256)
            if metric == "cpuacct.stat":
                yield "user", 512
                yield "system", 1024
            if metric == "cpu.stat":
                yield "nr_periods", 1
                yield "nr_throttled", 2
                yield "throttled_time", 3000000000  # Nano seconds
            if metric == "memory.limit_in_bytes":
                yield None, 4
            if metric == "memory.usage_in_bytes":
                yield None, 5

        with mock.patch('containerizer.cgroups.read_metrics', _metric):
            with mock.patch('containerizer.commands.usage.read_metrics', _metric):
                collect_container_stats("container-foo-bar", stats, 1)

        self.assertEqual(stats.cpus_limit, 1)
        self.assertEqual(stats.cpus_user_time_secs, 512)
        self.assertEqual(stats.cpus_system_time_secs, 1024)

        self.assertEqual(stats.cpus_nr_periods, 1)
        self.assertEqual(stats.cpus_nr_throttled, 2)
        self.assertEqual(stats.cpus_throttled_time_secs, 3)

        self.assertEqual(stats.mem_limit_bytes, 4)
        self.assertEqual(stats.mem_rss_bytes, 5)
