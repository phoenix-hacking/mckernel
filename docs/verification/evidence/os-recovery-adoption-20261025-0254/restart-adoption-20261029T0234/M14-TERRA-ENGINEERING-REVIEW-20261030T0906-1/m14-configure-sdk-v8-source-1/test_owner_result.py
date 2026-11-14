#!/usr/bin/env python3
"""Synthetic source-bound owner result evaluator only; no owner or physical execution."""
import ast, hashlib, json, pathlib, unittest
P=pathlib.Path(__file__).parent
src=ast.parse((P/'owner.successor.py').read_text()); fun=next(x for x in src.body if isinstance(x,ast.FunctionDef) and x.name=='_sdk13_driver_result')

def fail(v, msg):
    if not v: raise ValueError(msg)
def safe(p,label):
    if not p.is_file():raise ValueError(label)
    return p
def load(p,label):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ns={'Path':pathlib.Path,'_load_json':load,'_safe_regular':safe,'_fail':fail,'_sha256':sha,'SDK13_PROFILE_SHA':'p','SDK13_DRIVER_SHA':'d'}
exec(compile(ast.fix_missing_locations(ast.Module(body=[fun],type_ignores=[])),'owner.successor.py','exec'),ns)
check=ns['_sdk13_driver_result']
class OwnerResult(unittest.TestCase):
 def fixture(self,name):
    root=P/'owner-cases'/name;ev=root/'sdk13-driver-evidence';ev.mkdir(parents=True,exist_ok=False)
    cmds=[{'stage':'Configure ON composite','cwd':'/work','argv':['synthetic-cmake']},{'stage':'Post-generation verification','cwd':'/work','argv':['synthetic-verifier']}]
    def write(n,obj): (ev/n).write_text(json.dumps(obj))
    write('precompiler-view.json',{'status':'PASS_EFFECTIVE_MOUNTS_SOURCE_ENV','profile_sha256':'p','driver_sha256':'d','source_map_sha256':'s','mount_manifest_sha256':'m'})
    write('result.json',{'status':'COMMANDS_EXITED_ZERO','artifact_validation':'POST_GENERATION_STAGE_EXITED_ZERO_ONLY'})
    for i,c in enumerate(cmds,1):
        write('stage-%d-intent.json'%i,{'argv':c['argv'],'cwd':c['cwd']})
        write('stage-%d-result.json'%i,{'stage':c['stage'],'returncode':0,'direct_wait_completed':True,'timed_out':False})
        for ext in ('stdout','stderr'):(ev/('stage-%d.%s'%(i,ext))).write_text('synthetic')
    for name in ('output/build/tmp.resolve_MODULES_END/driver.ko','output/build/CMakeCache.txt','output/build/compile_commands.json'):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic')
    return root,ev,{'work':str(root),'commands':cmds},{'source_map_sha256':'s'},{'sha256':'m'}
 def test_accept_receipts_and_reject_changed_stage(self):
    root,ev,b,r,m=self.fixture('success');self.assertEqual(len(check(b,r,m)),3)
    stage=ev/'stage-2-result.json'; data=json.loads(stage.read_text());data['returncode']=1;stage.write_text(json.dumps(data))
    with self.assertRaises(ValueError):check(b,r,m)
 def test_missing_wait_and_binding_rejected(self):
    root,ev,b,r,m=self.fixture('missing_wait');stage=ev/'stage-1-result.json';data=json.loads(stage.read_text());data['direct_wait_completed']=False;stage.write_text(json.dumps(data))
    with self.assertRaises(ValueError):check(b,r,m)
    with self.assertRaises(ValueError):check(b,{'source_map_sha256':'bad'},m)
 def test_empty_artifact_rejected(self):
    root,ev,b,r,m=self.fixture('empty');(root/'output/build/compile_commands.json').write_text('')
    with self.assertRaises(ValueError):check(b,r,m)
if __name__=='__main__':unittest.main(verbosity=2)
