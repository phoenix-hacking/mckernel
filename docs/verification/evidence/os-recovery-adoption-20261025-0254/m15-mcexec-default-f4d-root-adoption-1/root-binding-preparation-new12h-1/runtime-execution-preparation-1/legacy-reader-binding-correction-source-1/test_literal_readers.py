"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Literal readers() preflight and tiny source/tool fixtures. No workload/context main.
"""
import ast,copy,hashlib,importlib.util,json,os,tempfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent.parent.parent
SELECTED=OLD.parent/'executor-integration-source-2/executor-sdk-user-rustc-source-4/target_tools_sdk_driver.RETAINED-PREFIX-SUFFIX.SOURCE-ONLY.py'
TRUTH=SELECTED.parent/'truthful-suffix-receipt-source-1'/SELECTED.name
NAMES={'need','digest','tool_digest'}
def ref(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def nodes(path):
    return [n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name in NAMES or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TOOL_RULES' for t in n.targets)]
def reject(fn):
    try:fn()
    except (RuntimeError,ValueError,OSError) as e:return str(e)
    raise AssertionError('negative reader control accepted')
def main():
    begin=time.monotonic();a=nodes(SELECTED);b=nodes(TRUTH);assert len(a)==len(b)==4
    same=ast.dump(ast.Module(body=a,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=b,type_ignores=[]),include_attributes=False);assert same
    old=load('retained_bad_observer',OLD/'observe_mcexec_context.py');new=load('corrected_literal_observer',HERE/'cohort/observe_mcexec_context.py')
    failure=reject(old.readers);assert failure=='accepted stable-reader source changed'
    env=new.readers();assert new.LEGACY==SELECTED and new.LEGACY_SHA==ref(SELECTED)['sha256']=='bb8be09522d6b4729dd7ca599b199a5b3060265636c8239af2a810059b6721a8'
    prep=json.loads((HERE/'cohort/PREPARATION.json').read_bytes());assert {k:v[1] for k,v in env['TOOL_RULES'].items()}==prep['target_tools']
    oldtree=ast.parse((OLD/'observe_mcexec_context.py').read_bytes());newtree=ast.parse((HERE/'cohort/observe_mcexec_context.py').read_bytes())
    # Normalize only the hash assignment to establish all other observer AST exact.
    for tree in (oldtree,newtree):
        for n in tree.body:
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='LEGACY_SHA' for t in n.targets):n.value=ast.Constant(value='HASH_BINDING_ONLY')
    assert ast.dump(oldtree,include_attributes=False)==ast.dump(newtree,include_attributes=False)
    checks=['original_literal_readers_failure_reproduced','four_extracted_nodes_and_TOOL_RULES_AST_exact','only_observer_hash_assignment_AST_changed','corrected_literal_readers_returns_actual_provider','actual_TOOL_RULES_match_preparation_target_tools']
    with tempfile.TemporaryDirectory(prefix='reader-fixture-',dir=HERE) as d:
        root=Path(d);f=root/'source';f.write_bytes(b'functional reader fixture\n');expected=hashlib.sha256(f.read_bytes()).hexdigest();assert env['digest'](f)==expected;checks.append('literal_digest_regular_fixture_pass')
        alias=root/'alias';alias.symlink_to(f.name);reject(lambda:env['digest'](alias));checks.append('digest_symlink_rejected')
        hard=root/'hard';os.link(f,hard);reject(lambda:env['digest'](f));hard.unlink();checks.append('digest_multilink_rejected')
        reject(lambda:env['tool_digest'](str(alias)));checks.append('unlisted_tool_alias_rejected')
        original_rules=copy.deepcopy(env['TOOL_RULES']);env['TOOL_RULES'][str(alias)]=('readonly-mounted-nightly',expected)
        result=env['tool_digest'](str(alias));assert result['sha256']==expected and result['resolved_path']==str(f) and result['first_metadata']==result['final_metadata']==result['path_metadata'];checks.append('literal_tool_digest_fixture_alias_stable_metadata_pass')
        env['TOOL_RULES'][str(alias)]=('readonly-mounted-nightly','0'*64);reject(lambda:env['tool_digest'](str(alias)));checks.append('wrong_tool_hash_rejected');env['TOOL_RULES']=original_rules
        changed=root/'changed-provider.py';changed.write_bytes(SELECTED.read_bytes()+b'\n');new.LEGACY=changed;reject(new.readers);checks.append('changed_whole_helper_source_rejected');new.LEGACY=SELECTED
        # Deterministic inode replacement after FD read exercises stable FD/path guard.
        realos=env['os'];fired=[False]
        class MutatingOS:
            def __getattr__(self,name):return getattr(realos,name)
            def read(self,fd,size):
                block=realos.read(fd,size)
                if block and not fired[0]:
                    replacement=root/'replacement';replacement.write_bytes(b'changed\n');replacement.replace(f);fired[0]=True
                return block
        env['os']=MutatingOS();reject(lambda:env['digest'](f));env['os']=realos;checks.append('stable_FD_source_replacement_rejected')
    proof=dict(status='PASS_LITERAL_READERS_AND_EXACT_PROVIDER_AST',scope=prep['scope'],provider_selected=ref(SELECTED),provider_prior=ref(TRUTH),extracted_ast_equal=same,extracted_nodes=[getattr(n,'name','TOOL_RULES') for n in a],extracted_ast_sha256=hashlib.sha256(ast.dump(ast.Module(body=a,type_ignores=[]),include_attributes=False).encode()).hexdigest(),old_failure=failure,checks=checks,seconds=time.monotonic()-begin,actual_context_main=False,actual_campaign_guard=False,actual_resource_observation=False,compiler_or_container=False,execution_authority=False)
    (HERE/'LITERAL-READER-PREFLIGHT.RESULT.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n');print(json.dumps(proof,sort_keys=True))
if __name__=='__main__':main()
