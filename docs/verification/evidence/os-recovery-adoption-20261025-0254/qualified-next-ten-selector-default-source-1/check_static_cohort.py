"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Real source/API/config/profile/metadata preflight; no compiler, Root or workload.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel');BASE=E/'ROOT-F03-F06-QUALIFIED-DEFAULT-BUILD-ADMISSION-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 plan=json.loads((D/'COHERENT-TEN-SELECTOR-SOURCE-PLAN.NOT-GRANTED.json').read_text());p=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text());expected=json.loads((D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text());export=json.loads((D/'INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json').read_text());old=json.loads((BASE/'PROFILE.SOURCE-ONLY.json').read_text())
 for rel,row in plan['preimages'].items():assert ref(R/rel)==row
 for rel,row in plan['postimages'].items():
  assert ref(Path(row['path']))==row
  if rel not in plan['preimages']:assert not (R/rel).exists()
 prior=json.loads((E/'qualified-cohort-next-static-source-1/COHERENT-NEXT-SOURCE-PLAN.NOT-GRANTED.json').read_text())
 for rel,row in prior['source_postimages'].items():assert ref(R/rel)['sha256']==row['sha256'],('accepted685 canonical changed',rel)
 grant=json.loads((BASE/'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json').read_text());source=BASE/'run_build_only.py';assert ref(source)==grant['runner']
 spec=importlib.util.spec_from_file_location('accepted_four_command_source_API',source);runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
 directory_rows=runner.source_directory_postimages(p);assert len(directory_rows)==105
 refs=[r['source'] for r in p['inputs']['configuration']]+[r['source'] for r in p['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in p['inputs']['postimages']]+[r['postimage'] for r in directory_rows]
 assert export['qualified_readonly_files']==refs
 for row in refs:runner.auth(row)
 # This is a pure parser vector, not an actual Root request or grant.
 parser_vector=copy.deepcopy(p);parser_vector['request_sha256']='a'*64;assert len(runner.commands_for_plan(parser_vector))==4
 assert [r for r in p['inputs']['objects'] if not r['replace']]==[r for r in old['inputs']['objects'] if not r['replace']]
 assert p['exact_commands'][-1]==old['exact_commands'][-1]
 assert p['request_sha256'] is None and p['native_custody_clearance'] is None
 assert all(export[k] is None for k in ['author','decision','request_sha256','runtime_authority'])
 assert len(expected['all_Rust_exports'])==33 and len(expected['new_unique_Rust_exports'])==8 and len(expected['direct_existing_Rust_exports'])==2
 for cfg in plan['new_Rust_cfgs']:assert p['exact_commands'][0]['argv'].count(cfg)==1
 assert 'f06_use_nocache_mmap' not in p['exact_commands'][0]['argv']
 for path in [D/'qualify_produced_cohort.py',*list((D/'validator-templates').glob('*.py'))]:ast.parse(path.read_text(),filename=str(path))
 print(json.dumps(dict(scope=__doc__.splitlines()[0],status='PASS_FROZEN_SOURCE_REAL_FOUR_COMMAND_API_105FILE_CLOSURE_AND_PREPUBLISHED_ACCEPTANCE_INPUTS',runtime_authority=None,commands=4,retained_C_inputs=8,new_unique_Rust_exports_expected=8,new_C_wrappers_expected=10,Rust_files=105,compiler_guest_Root_grant_actions=0)))
if __name__=='__main__':main()
