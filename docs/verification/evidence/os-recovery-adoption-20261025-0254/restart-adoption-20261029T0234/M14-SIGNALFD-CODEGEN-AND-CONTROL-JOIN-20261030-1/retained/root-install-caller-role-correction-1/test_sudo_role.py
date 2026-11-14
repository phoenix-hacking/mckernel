"""Functional-only synthetic argv/ancestry regression; UNRUN, no processes."""
import importlib.util
import unittest
from pathlib import Path

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('test_sudo_role_caller',HERE/'prepare_and_exec.py')
caller=importlib.util.module_from_spec(spec);spec.loader.exec_module(caller)


def argv(*parts):return b'\0'.join(part.encode() for part in parts)+b'\0'


class SudoRole(unittest.TestCase):
    def test_sudo_containing_full_command_never_becomes_root_python(self):
        boot='pinned bootstrap literal';wait='pinned installer literal'
        def row(pid,ppid,pgrp):return {'pid':pid,'ppid':ppid,'pgrp':pgrp,'uid':0,'birth':str(pid)}
        sudo=row(3109448,3109447,3109447)
        root=row(3109451,3109448,3109447)
        keeper=row(3109452,3109451,3109447)
        installer=row(3109453,3109452,3109453)
        sudo_cmd=argv('/usr/bin/sudo','-A','/usr/bin/taskset','-c','6','/usr/bin/prlimit','--','/usr/bin/python3','-I','-B','-c',boot,'admission','review')
        root_cmd=argv('/usr/bin/python3','-I','-B','-c',boot,'admission','review')
        install_cmd=argv('/usr/bin/python3','-I','-B','-c',wait,'inherited-args')
        early={sudo['pid']:(sudo,sudo_cmd),root['pid']:(root,root_cmd)}
        self.assertEqual(caller.identify_roles(early,sudo['pid'],boot,wait),{'root_parent':root})
        full=dict(early);full[keeper['pid']]=(keeper,root_cmd);full[installer['pid']]=(installer,install_cmd)
        self.assertEqual(caller.identify_roles(full,sudo['pid'],boot,wait),
                         {'root_parent':root,'keeper':keeper,'installer':installer})


if __name__=='__main__':unittest.main()
