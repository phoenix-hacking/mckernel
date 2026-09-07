"""Exercise the guest cleanup probe's actual Linux PCP accounting parser."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NativeImageMemoryAccountingTests(unittest.TestCase):
    def test_node_and_zone_scoping_short_reads_and_malformed_records(self):
        cc = shutil.which("cc")
        if cc is None:
            self.skipTest("C compiler unavailable")
        source = (ROOT / "scripts/tests/fixtures/native-image-load.c").read_text()
        start = "static unsigned long node_cached_free_kib(int wanted_node)"
        end = "static void expect_load("
        self.assertEqual(source.count(start), 1)
        self.assertEqual(source.count(end), 1)
        body = source[source.index(start):source.index(end)]
        prelude = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#define SYS_OPEN 2
#define SYS_READ 0
#define require(test) do { if (!(test)) exit(101); } while (0)
static char zone_information[65536];
static long call(long nr, long fd, long address, long length)
{
    if (nr == SYS_OPEN) {
        require(strcmp((const char *)fd, "/proc/zoneinfo") == 0);
        require(address == 0 && length == 0);
        return 3;
    }
    require(nr == SYS_READ && fd == 3);
    if (length > 37) length = 37;
    return read(0, (void *)address, length);
}
static void close_fd(int fd) { require(fd == 3); }
"""
        main = r"""
int main(int argc, char **argv)
{
    require(argc == 2);
    printf("%lu\n", node_cached_free_kib(atoi(argv[1])));
    return 0;
}
"""
        records = """Node 0, zone DMA
  pages free 100
  pagesets
    cpu: 0
              count:    9
              high:     1000
              high_min: 200
Node 1, zone Normal
  pagesets
    cpu: 0
              count:    900
    cpu: 1
              count:    7
Node 0, zone DMA32
  pagesets
    cpu: 0
              count:    512
Node 0, zone Device
  pages free 0
"""
        cases = [(0, records, 0, "2084\n"), (1, records, 0, "3628\n"),
                 (0, "Node 0, zone DMA\n  pagesets\n count: 0\n", 0, "0\n"),
                 (2, records, 101, ""),
                 (0, "Node 0, zone DMA\n count: invalid\n", 101, ""),
                 (0, "Node x, zone DMA\n count: 1\n", 101, ""),
                 (0, "Node 0, zone DMA\n count: 1\n" + "x" * 65536, 101, "")]
        with tempfile.TemporaryDirectory(prefix="native-image-pcp-") as temporary:
            fixture = Path(temporary) / "parser.c"
            fixture.write_text(prelude + body + main)
            binary = Path(temporary) / "parser"
            result = subprocess.run([cc, "-O2", "-Wall", "-Wextra", "-Werror", str(fixture), "-o", str(binary)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for node, data, expected_code, expected_output in cases:
                result = subprocess.run([str(binary), str(node)], input=data, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
                self.assertEqual(result.returncode, expected_code, result.stderr)
                self.assertEqual(result.stdout, expected_output)


if __name__ == "__main__":
    unittest.main()
