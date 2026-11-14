"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only reviewed dependency DATA fill; no guard call, capture, query or workload.
"""
from pathlib import Path
import argparse
import json
import observe_current62_bfd_postjoin as m

D=Path(__file__).resolve().parent
def create(path,value):
 with Path(path).open('x')as stream:json.dump(value,stream,indent=2);stream.write('\n')

def bind(source):
 q=m.checked(m.ref(source))
 m.need(q['author']=='/root'and q['decision']=='BIND_REVIEWED_ROOT62_HISTORY_DEPENDENCIES_SOURCE_ONLY'and q['runtime_authority']is None,'Root-only source/data fill')
 for key in ['guard_configuration','physical_configuration','common_dependency_review','Root61_dependency_review']:m.auth(q[key])
 config=m.checked(q['guard_configuration'])
 m.need(config['operation']==m.PINS['new_operation']and config['shared_guard']==m.PINS['shared_guard'],'exact new postjoin operation config')
 guard=m.load(m.PINS['guard_adapter'],'pure_current62_dependency_configuration');guard.configure(q['guard_configuration'])
 m.need(all(0<limit<=ceiling for limit,ceiling in zip(guard.current_cutoffs(),m.PINS['limits'])),'current or tighter limits; pure configuration only')
 physical=m.checked(q['physical_configuration'])
 m.need(physical['guard_adapter']==m.PINS['guard_adapter']and physical['guard_config']==q['guard_configuration'],'same new operation at physical history depth')
 common=m.checked(m.ref(D/'history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json'))
 common.update(author='/root',account_window_guard_configuration=q['guard_configuration'],physical_history_configuration=q['physical_configuration'],independent_dependency_review=q['common_dependency_review'])
 cr=m.checked(q['common_dependency_review'])
 m.need(cr['independent']is True and cr['implementation_ownership']is False and cr['decision']=='PASS_EXACT_ROOT59_CONFIGURED_NEW_WINDOW_OBSERVER_DEPENDENCIES'and cr['reviewed_observer']==common['observer'],'independent exact common dependency review')
 for key in ['account_window_guard','account_window_guard_configuration','physical_history_observer','physical_history_configuration']:m.need(cr['reviewed_'+key]==common[key],'exact common '+key)
 top=m.checked(m.ref(D/'history/ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json'));top.update(author='/root',guard_configuration=q['guard_configuration'],independent_review=q['Root61_dependency_review'])
 tr=m.checked(q['Root61_dependency_review'])
 m.need(tr['independent']is True and tr['implementation_ownership']is False and tr['decision']=='PASS_EXACT_ROOT61_BFD_OBSERVER_DEPENDENCIES'and tr['observer']==top['observer'],'independent exact historical61 dependency review')
 for key in ['guard_adapter','guard_configuration']:m.need(tr[key]==top[key],'exact historical61 '+key)
 create(D/'history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json',common)
 create(D/'history/ROOT61-RUNTIME-DEPENDENCIES.json',top)
 pins=m.checked(m.ref(D/'history/ACTUAL-PINS.TEMPLATE.NOT-AUTHORITY.json'));pins['common_dependencies']=m.ref(D/'history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json')
 create(D/'history/ACTUAL-PINS.json',pins)
 return dict(status='ROOT62_HISTORY_DATA_BOUND_NOT_EXECUTION_AUTHORITY',common_dependencies=m.ref(D/'history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json'),historical61_dependencies=m.ref(D/'history/ROOT61-RUNTIME-DEPENDENCIES.json'),current60_pins=m.ref(D/'history/ACTUAL-PINS.json'),runtime_authority=None)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);parser.add_argument('--root-input',type=Path,required=True);args=parser.parse_args();print(json.dumps(bind(args.root_input),indent=2))
