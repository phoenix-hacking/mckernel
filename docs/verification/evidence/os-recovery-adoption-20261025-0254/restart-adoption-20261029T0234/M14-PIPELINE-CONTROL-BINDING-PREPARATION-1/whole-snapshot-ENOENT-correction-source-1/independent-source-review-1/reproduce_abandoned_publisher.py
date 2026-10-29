"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic process ownership/admission counterexample. No real proc or process call.
"""
from pathlib import Path
import hashlib, importlib.util, json
D=Path(__file__).resolve().parent
P=D.parent
def ref(p):
    raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
source=P/'retire_exact_current118_stopped_container.py'
assert ref(source)['sha256']=='b09a8b895209218995f039d5aac2c42b4d28779c0b311b85184168566f4f7d18'
spec=importlib.util.spec_from_file_location('TEST_ONLY_existing_proc_leaves',P/'test_whole_snapshot_retry.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class AbandonedPublisher(m.Proc):
    def listdir(self,path):
        assert path=='/proc';self.listings+=1
        return ['1','100','150','200'] if self.affected() else ['1','100','300']
    def readlink(self,path):
        self.fault(path,'exe')
        return '/usr/bin/rustc' if path=='/proc/150/exe' else '/bin/unit'
fake=AbandonedPublisher()
error,out,events=fake.execute()
report=json.loads(out)
assert error is None and report['publishers']==[]
assert fake.listings==3 and len(events)==1 and events[0]['filename']=='/proc/200/stat'
v=dict(scope=__doc__.splitlines()[0],status='REPRODUCED_DISCARDED_OBSERVED_PUBLISHER',executor=ref(source),test_source=ref(P/'test_whole_snapshot_retry.py'),first_attempt=[1,100,'150 executable /usr/bin/rustc','200 /proc/stat ENOENT'],accepted_attempts=[[1,100,300],[1,100,300]],error=None,emitted_publishers=report['publishers'],abandoned_events=events,original_publisher_predicate=m.CODE[m.CODE.index('def publisher'):m.CODE.index('def _snapshot_once')],conclusion='The original publisher predicate identifies rustc150 before unrelated200 disappears, but whole-snapshot restart discards publishers150 and emits a clean report. This violates preservation of observed functional operation/custody facts.',real_proc_root_Popen_Docker_signal_calls=0,runtime_authority=None)
(D/'ABANDONED-PUBLISHER.COUNTEREXAMPLE.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(ref(D/'ABANDONED-PUBLISHER.COUNTEREXAMPLE.json')))
