"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual Resource1 raw evidence; synthetic supplement/authority only in memory.
"""
import copy,runpy
from pathlib import Path
v=runpy.run_path(str(Path(__file__).with_name('test_observer_stage.py')));m=v['m'];checker=v['checker'];actors=v['stage_actors'];context=dict(v['context'],nonce='11111111111111111111111111111111')
resource=m.read(m.RESOURCE1);helper=m.read(m.RESOURCE_JOIN);parent=m.read(m.RESOURCE_PARENT);release=m.read(m.RESOURCE_RELEASE);refusal=m.read(m.RESOURCE_REFUSAL);review=m.read(m.RESOURCE_REVIEW)
selfrow=resource['current_physical_observation']['observer_self'];clients=resource['current_physical_observation']['query_clients']
added=[dict(pid=parent['child']['pid'],start=parent['child']['birth'],role='CURRENT119_resource1_wrapper',group=parent['child']['pgrp'],fd=None),dict(pid=parent['parent']['pid'],start=parent['parent']['birth'],role='CURRENT119_resource1_outer_parent',group=None,fd=None),dict(pid=selfrow['pid'],start=selfrow['birth'],role='CURRENT119_resource1_observer',group=selfrow['group'],fd=None)]+[dict(pid=r['pid'],start=r['birth'],role='CURRENT119_resource1_query_client',group=r['pid'],fd=None)for r in clients]
unknown=dict(outer_tool=dict(pid=2581701,birth=None),data_binder=dict(pid=None,birth=None),refused_entry=dict(tool_session=529721,pid=None,birth=None,status='UNKNOWN'),inherited_physical_helper_births='UNKNOWN')
sref=m.RESOURCE_CUSTODY;supp=m.read(sref);abandonment=m.read(m.ABANDONMENT);failure=m.read(m.FAILURE_REVIEW)
authority=dict(post_root68_resource1_custody_supplement=sref)
def run(ss=supp,aa=authority,cc=context,rr=resource,hh=helper,pp=parent,ll=release,ff=refusal,vv=review,ab=abandonment,fa=failure):return m.append_resource1(actors,ss,sref,aa,cc,checker,rr,hh,pp,ll,ff,vv,ab,fa)
out=run();assert out[:len(actors)]==actors and len(out)==207 and len({(x['pid'],x['start'])for x in out})==202
checks=[('supp','refused_nonce_disposition','AVAILABLE'),('supp','all_post_root68_custody_listed',False),('supp','old_readonly_client_status','known'),('supp','resource',{}),('supp','refusal',{}),('authority','post_root68_resource1_custody_supplement',{}),('context','nonce',supp['refused_nonce']),('helper','direct_child_joined',False),('parent','signals_sent',1),('parent','process_group_absent',False),('release','native_execution_authority','granted'),('refusal','claim_present',True),('review','independent',False),('review','native_acceptance',True)]
for obj,key,value in checks:
 d=copy.deepcopy(dict(supp=supp,authority=authority,context=context,resource=resource,helper=helper,parent=parent,release=release,refusal=refusal,review=review));d[obj][key]=value
 try:run(d['supp'],d['authority'],d['context'],d['resource'],d['helper'],d['parent'],d['release'],d['refusal'],d['review'])
 except (ValueError,AssertionError,KeyError):continue
 raise AssertionError('accepted wrong '+obj+'.'+key)
bad=copy.deepcopy(supp);bad['unmeasured']['refused_entry']['birth']=110000000
try:run(ss=bad)
except (ValueError,AssertionError,KeyError):pass
else:raise AssertionError('invented refused bridge birth accepted')
print('PASS actual closed Resource1 evidence + Root V2 supplement (authority context synthetic): 207 retained rows/202 identities; 15 negative mutations; unknown births and abandoned nonce enforced. No live operations.')
