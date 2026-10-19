"""Prepare source-bound accepted engines after genuine facts exist; never execute."""
from pathlib import Path
import argparse,ast,json,types
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from terminal_contract import checked_bytes,validate_known,bind_engine_config,need,digest
from remaining_path_bindings import specialize_cleanup_source,specialize_observer_source
HERE=Path(__file__).resolve().parent
CONFIGURATOR=Path('/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/configure_fourleaf_terminal.py')

def configure(known,late,config):
 bind_engine_config(known,late)
 # Every config input must already be immutable and refer to THIS late operation.
 for key in ('physical','pairs','selected_provenance','canonical_report','canonical_gate','canonical_binding'):checked_bytes(config[key],128<<20)
 need(config['canonical_gate']['path']==str(HERE/'future_stage_case.py'),'additive future canonical gate')
 need(config['canonical_report']==late['artifact_report'],'actual artifact authority')
 raw=checked_bytes(known['configurator']);source=raw.decode();tree=ast.parse(source)
 cleanup=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='configure_cleanup');fn=ast.get_source_segment(source,cleanup)
 old="Path('/home/holden/mckernel/scripts/native_rust_cutover_image_terminal_cleanup.py').read_text()"
 need(fn.count(old)==1,'exact accepted cleanup specialization boundary');fn=fn.replace(old,"Path("+repr(known['engines']['cleanup']['path'])+").read_text()")
 # Existing code has exactly two guard-name literals; replace the predecessor
 # known source string with the genuine new guard capture stem, never a CID.
 line=next(l for l in fn.splitlines() if "old_guard='native-rust-" in l)
 replacement=" old_guard="+repr(known['predecessor_guard_name'])+";current_guard=Path(physical['guard']['path']).parent.name;assert source.count(old_guard)==2;source=source.replace(old_guard,current_guard)"
 fn=fn.replace(line,replacement)
 m=types.ModuleType('_exact_future_configurator');m.__file__=known['configurator']['path'];exec(compile(raw,m.__file__,'exec'),m.__dict__)
 m.T=HERE;m.R=Path(known['request']['path']).parent;m.BASE=Path(known['engines']['observer']['path']);exec(compile(fn,m.__file__,'exec'),m.__dict__)
 roles=json.loads(checked_bytes(known['future_roles']));actual=[]
 for role,pair in zip(sorted(late['roles']),[None]*len(late['roles'])):
  authority=next(p for p in late['pairs'] if p['original']['path']==late['roles'][role]['original'])
  actual.append(dict(kind=role,original=authority['original'],retained=authority['retained']['path']))
 # The accepted configurator expects this exact finite authority filename.
 p=HERE/'actual21-retention-authorities.json'
 with p.open('x') as f:json.dump(actual,f,sort_keys=True,indent=2);f.write('\n')
 cleanup_source=specialize_cleanup_source(m.configure_cleanup(config),known)
 with (HERE/'cleanup_fourleaf.py').open('x') as f:f.write(cleanup_source)
 observer_source=specialize_observer_source(m.configure(config),known)
 with (HERE/'observe_four_leaf_image_retirement.py').open('x') as f:f.write(observer_source)
 return dict(status='PREPARED_GENUINE_BOUND_ENGINE_SOURCES_NOT_EXECUTED',observer=str(HERE/'observe_four_leaf_image_retirement.py'),cleanup=str(HERE/'cleanup_fourleaf.py'),root_or_cleanup_authority=False)

def main():
 p=argparse.ArgumentParser()
 for stem in ('known','late','config'):p.add_argument('--'+stem,required=True);p.add_argument('--'+stem+'-sha256',required=True)
 x=p.parse_args();values={k:json.loads(checked_bytes(dict(path=getattr(x,k),sha256=getattr(x,k+'_sha256')),128<<20)) for k in ('known','late','config')}
 print(json.dumps(configure(**values),sort_keys=True))
if __name__=='__main__':main()
