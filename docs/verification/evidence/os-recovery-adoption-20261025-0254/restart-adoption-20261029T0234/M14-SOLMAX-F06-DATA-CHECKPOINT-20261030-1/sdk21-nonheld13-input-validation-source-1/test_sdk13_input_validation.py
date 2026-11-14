"""Pure SDK13 input validator fixture; functional OS only; no security testing.
Synthetic temporary paths plus frozen profile/proposal data. No runner/owner launch.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('sdk13_inputs',HERE/'sdk13_input_validation.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
BASE=HERE.parent
PROFILE=BASE/'sdk21-nonheld13-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json'
PROPOSAL=BASE/'sdk21-nonheld13-admission-successor-1/ADMISSION-SUCCESSOR.SOURCE-ONLY.json'

class Inputs(unittest.TestCase):
    def test_exact_selection_and_held_mutation(self):
        profile=json.loads(PROFILE.read_bytes()); proposal=json.loads(PROPOSAL.read_bytes())
        m._selectors(profile,proposal)
        altered=copy.deepcopy(profile); altered['commands'][0]['argv'] += ['--cfg','f03_direct_tid_candidate']
        other=copy.deepcopy(proposal); other['compiler_commands']=altered['commands']
        with self.assertRaisesRegex(ValueError,'held or overlapping'): m._selectors(altered,other)
        altered=copy.deepcopy(profile); altered['commands'][0]['argv'] += ['--cfg','f06_handler_commit_candidate']
        other=copy.deepcopy(proposal); other['compiler_commands']=altered['commands']
        with self.assertRaisesRegex(ValueError,'held or overlapping'): m._selectors(altered,other)
        altered=copy.deepcopy(profile); altered['commands'][2]['argv'].remove('-DMCKERNEL_RUST_F06_DO_SIGNAL_WHOLE')
        other=copy.deepcopy(proposal); other['compiler_commands']=altered['commands']
        with self.assertRaisesRegex(ValueError,'paired C selector'): m._selectors(altered,other)

    def test_mount_order_and_writable_rejection(self):
        proposal=json.loads(PROPOSAL.read_bytes())
        mounts=[(r['host'],r['container'],r['mode']=='ro') for r in proposal['mounts_proposed']]
        m._mount_graph(mounts)
        bad=list(mounts); h,t,_=bad[2]; bad[2]=(h,t,False)
        with self.assertRaisesRegex(ValueError,'unexpected writable'): m._mount_graph(bad)
        bad=list(mounts); bad[1],bad[2]=bad[2],bad[1]
        with self.assertRaisesRegex(ValueError,'order masks child'): m._mount_graph(bad)

    def test_tree_complete_bytes_and_symlink_escape(self):
        with tempfile.TemporaryDirectory(prefix='sdk13-input-fixture-') as tmp:
            root=Path(tmp)/'tree'; root.mkdir(); (root/'dir').mkdir(); f=root/'dir/file.rs'; f.write_bytes(b'fixture')
            rows=[{'relative':'dir','kind':'dir'},{'relative':'dir/file.rs','kind':'file','bytes':7,'sha256':hashlib.sha256(b'fixture').hexdigest()}]
            m._tree(root,rows)
            f.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'inventory or bytes differ'): m._tree(root,rows)
            f.write_bytes(b'fixture'); (root/'extra').write_text('x')
            with self.assertRaisesRegex(ValueError,'inventory or bytes differ'): m._tree(root,rows)
            (root/'extra').unlink(); (root/'escape').symlink_to(Path(tmp))
            with self.assertRaisesRegex(ValueError,'symlink escapes'): m._tree(root,rows)

    def test_work_creation_binding_and_tamper(self):
        with tempfile.TemporaryDirectory(prefix='sdk13-work-fixture-') as tmp:
            path=Path(tmp)/'work'; path.mkdir(mode=0o700)
            bound={'work':path,'work_identity':None}; observed=m._identity(path.stat())
            with self.assertRaisesRegex(ValueError,'identity differs'): m.bind_work(bound,{},observed[:-1]+(observed[-1]+1,))
            m.bind_work(bound,{},observed)
            (path/'owner-output').write_text('synthetic')
            current=path.stat()
            self.assertEqual(bound['work_identity'],m._directory_identity(current))
            with self.assertRaisesRegex(ValueError,'already bound'): m.bind_work(bound,{},m._identity(current))

    def test_revalidation_requires_original_request_core(self):
        with tempfile.TemporaryDirectory(prefix='sdk13-revalidate-fixture-') as tmp:
            path=Path(tmp)/'future'; bound={'work':path,'work_identity':None,'profile_path':'p','request_path':'q','source_map_path':'s',
                     'snapshot':{'test':1},'mounts':[],'commands':[],'request_sha256':'a'}
            fresh={'snapshot':{'test':1},'mounts':[],'commands':[],'request_sha256':'a'}
            with mock.patch.object(m,'_collect',return_value=fresh): m.revalidate(bound,{})
            fresh['request_sha256']='b'
            with mock.patch.object(m,'_collect',return_value=fresh):
                with self.assertRaisesRegex(ValueError,'input identity changed'): m.revalidate(bound,{})

if __name__=='__main__': unittest.main(verbosity=2)
