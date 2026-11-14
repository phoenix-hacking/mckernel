"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic parser controls only; no ELF execution/compiler/install occurs.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import validate_consumer as v


class ConsumerTests(unittest.TestCase):
    def test_capture_oracles(self):
        root = Path(__file__).resolve().parent
        contract = json.loads((root/'CONSUMER-CONTRACT.json').read_bytes())
        usage = (root/'expected-usage.stderr').read_bytes()
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            dest = Path(tmp)
            for key, path in [('installed_cli','usr/local/sbin/ihkconfig'),('installed_library','usr/local/lib64/libihk.so')]:
                data = key.encode();p = dest/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
                contract['accepted_artifacts'][key] = dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
            captures = [dict(index=i,argv=argv,environment=contract['expected_environment'],direct_child_joined=True,group_absent=True,closed_streams=True,timed_out=False,returncode=1 if i>=4 else 0,stdout='',stderr='') for i,argv in enumerate(contract['expected_capture_argv'])]
            captures[0]['stdout']=''.join('00000001 '+kind+' '+name+'\n' for name,kind in contract['roots'].items())
            captures[2]['stdout']=''.join(' U '+name+'\n' for name in contract['project_imports'])
            captures[3]['stdout']=' libihk.so => '+str(dest/'usr/local/lib64/libihk.so')+' (0x1234)\n'
            for i in (4,5):captures[i]['stderr']=usage.decode()
            self.assertEqual(v.validate(contract,captures,usage,dest)['real_cli_main_cases'],2)
            controls=[(0,'stdout',captures[0]['stdout'].replace(' T ihk_os_boot\n',' U ihk_os_boot\n')),
                      (1,'stdout',' U ihk_os_boot\n'),(2,'stdout',' U ihk_os_boot\n'),
                      (3,'stdout',' libihk.so => /wrong/libihk.so (0x1234)\n'),
                      (4,'returncode',0),(4,'stderr',''),(5,'stdout','unexpected'),
                      (0,'direct_child_joined',False),(1,'group_absent',False),(2,'closed_streams',False),
                      (4,'argv',['/wrong/cli']),(4,'environment',{'LD_PRELOAD':'bad'}),(3,'stderr','loader warning')]
            for index,key,value in controls:
                with self.subTest(index=index,field=key):
                    bad=copy.deepcopy(captures);bad[index][key]=value
                    with self.assertRaises(ValueError):v.validate(contract,bad,usage,dest)
            (dest/'usr/local/sbin/ihkconfig').write_bytes(b'different')
            with self.assertRaisesRegex(ValueError,'installed bytes'):v.validate(contract,captures,usage,dest)


if __name__=='__main__':unittest.main(verbosity=2)
