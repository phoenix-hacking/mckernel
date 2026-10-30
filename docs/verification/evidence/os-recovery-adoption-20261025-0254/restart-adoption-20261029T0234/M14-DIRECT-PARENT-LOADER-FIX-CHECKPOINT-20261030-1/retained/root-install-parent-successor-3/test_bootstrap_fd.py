"""Functional-only source regression; UNRUN, all fd/signal operations mocked."""
import importlib.util
import json
import hashlib
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).parent


def bootstrap():
    spec=importlib.util.spec_from_file_location('test_parent_bootstrap',HERE/'BOOTSTRAP.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


class TestAncestors(unittest.TestCase):
    def setUp(self):
        self.b=bootstrap();self.nextfd=20;self.active=set();self.maximum=0;self.closes=[]
    def opened(self,path,flags,dir_fd=None):
        if dir_fd is not None:self.assertIn(dir_fd,self.active)
        fd=self.nextfd;self.nextfd+=1;self.active.add(fd);self.maximum=max(self.maximum,len(self.active));return fd
    def closed(self,fd):
        self.assertIn(fd,self.active);self.active.remove(fd);self.closes.append(fd)
    def test_repeated_paths_keep_leaves_and_bound_live_descriptors(self):
        with mock.patch.object(self.b.signal,'pthread_sigmask',return_value=set()), \
             mock.patch.object(self.b.os,'open',side_effect=self.opened), \
             mock.patch.object(self.b.os,'close',side_effect=self.closed):
            leaves=[self.b.open_absolute('/a/b/c/file%d'%i) for i in range(3)]
        self.assertEqual(self.active,set(leaves));self.assertLessEqual(self.maximum,len(leaves)+1)
        self.assertEqual(len(self.closes),len(set(self.closes)))
        self.assertEqual(sum(r['state']=='OWNED' for r in self.b.hold),3)
        self.assertTrue(all(r['fd'] is None for r in self.b.hold if r['state']=='VERIFIED_CLOSED'))
    def test_uncertain_close_is_recorded_and_never_retried(self):
        def uncertain(fd):self.closes.append(fd);raise InterruptedError('ambiguous close')
        with mock.patch.object(self.b.signal,'pthread_sigmask',return_value=set()), \
             mock.patch.object(self.b.os,'open',side_effect=self.opened), \
             mock.patch.object(self.b.os,'close',side_effect=uncertain):
            with self.assertRaises(InterruptedError):self.b.open_absolute('/a/b')
        self.assertEqual(len(self.closes),1)
        failed=[r for r in self.b.hold if r['state']=='CLOSURE_UNKNOWN']
        self.assertEqual(len(failed),1);self.assertIsNone(failed[0]['fd'])
        self.assertEqual(failed[0]['historical_fd'],self.closes[0])
        self.assertEqual(sum(r['state']=='OWNED' for r in self.b.hold),1)
    def test_open_failure_keeps_previous_ancestor(self):
        def failing(path,flags,dir_fd=None):
            if path=='a':raise OSError('synthetic failure')
            return self.opened(path,flags,dir_fd)
        with mock.patch.object(self.b.signal,'pthread_sigmask',return_value=set()), \
             mock.patch.object(self.b.os,'open',side_effect=failing), \
             mock.patch.object(self.b.os,'close',side_effect=self.closed):
            with self.assertRaises(OSError):self.b.open_absolute('/a/b')
        self.assertEqual(self.closes,[])
        self.assertEqual([r['state'] for r in self.b.hold],['OWNED','OPEN_UNKNOWN'])
    def test_profile_literal_and_limits(self):
        profile=json.loads((HERE/'PROFILE.SOURCE-ONLY.json').read_text());argv=profile['argv']
        raw=(HERE/'BOOTSTRAP.py').read_bytes()
        self.assertEqual(len(argv),20);self.assertEqual(argv[4],'6');self.assertEqual(argv[15],'-c')
        self.assertEqual(argv[16].encode(),raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),profile['bootsource_sha256'])
        self.assertIn('--nofile=256:256',argv)


if __name__=='__main__':unittest.main()
