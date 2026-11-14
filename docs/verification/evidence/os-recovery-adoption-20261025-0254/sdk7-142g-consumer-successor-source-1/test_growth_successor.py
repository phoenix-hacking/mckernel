"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure changed-contract regressions; no owner imports, clocks, queries or workloads.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
import growth_successor as g

D = Path(__file__).resolve().parent
P = D.parent / 'm15-sdk7-current-authority-composition-source-1'
OLD = D.parent / 'new-window-daemon-sdk-source-1/current-installed-daemon7-source-2/daemon_sdk_owner.EXACT-DRIVER-HASH.py'

def ref(name):
    return dict(path=name, bytes=1, sha256='0'*64)

class Growth(unittest.TestCase):
    def fixture(self):
        native = ref('native2'); native['sha256'] = g.NATIVE2_SHA
        bundle = dict(latest_operation=native, growth_closure=ref('growth'))
        head = dict(schema='mckernel.serial-operation-head.v2', latest_container_operation=native,
                    latest_serial_operation=ref('growth'), physical_prerequisites=[ref('growth')],
                    no_unlisted_intervening_operation=True, consumed_nonces=['native', 'grow'])
        latest = dict(nonce='native', closed_wall=100)
        request = dict(nonce='new', backing_identity={k:v for k,v in g.AFTER.items() if k!='uuid'})
        live = dict(actual_backing_identity=g.AFTER, growth_closure=ref('growth'),
                    latest_serial_operation=ref('growth'), clock=dict(wall=104))
        window = dict(boot_id='boot')
        growth = dict(schema='mckernel.scratch-growth-closure.v1',kind='scratch_ext4_110_to_142g',
                      status='PASS_SCRATCH_GROWTH_CLOSED', previous_serial_operation=native,
                      nonce='grow',boot_id='boot',before=g.BEFORE,after=g.AFTER,closed_wall=102,
                      **{k:ref(k) for k in ('source','grant','execution_review','actual_commands',
                                           'normal_fd_release','fresh_physical_acceptance')})
        binding=dict(source=ref('source'),previous_serial_operation=native,nonce='grow',before=g.BEFORE,after=g.AFTER)
        docs=dict(growth=growth,source=b'finite source',
                  grant=dict(status='GRANTED_SCRATCH_GROWTH_110_TO_142G',bindings=binding,lower_reserves=False,commands=[['exact','growth']]),
                  execution_review=dict(decision='PASS_SCRATCH_GROWTH_EXECUTION',implementation_ownership=False,reviewer='independent',grant=ref('grant'),bindings=binding),
                  actual_commands=dict(status='PASS_ACTUAL_SCRATCH_GROWTH_COMMANDS',grant=ref('grant'),argv=[['exact','growth']],returncodes=[0]),
                  normal_fd_release=dict(status='PASS_NORMAL_FD_RELEASE',grant=ref('grant'),fd_closed=True,holder_retired=True,group_absent=True,closed_streams=True,closed_wall=101),
                  fresh_physical_acceptance=dict(decision='PASS_SCRATCH_GROWTH_CURRENT_PHYSICAL',implementation_ownership=False,reviewer='independent',actual_backing_identity=g.AFTER,observed_wall=103,
                     bindings=dict(binding,**{k:ref(k) for k in ('grant','execution_review','actual_commands','normal_fd_release')})))
        return [bundle,head,latest,request,live,window,docs]
    def call(self, fixture):
        args=fixture[:-1];docs=fixture[-1]
        return g.growth_chain(*args,load=lambda r,*_:copy.deepcopy(docs[r['path']]))
    def test_exact_growth_chain_and_container_separation(self):
        f=self.fixture();self.assertEqual(self.call(f)['after'],g.AFTER)
        self.assertNotIn('no_intervening_operation',f[1])
        self.assertNotIn('container',f[-1]['growth'])
    def test_broken_chain_evidence_identity_and_clock_rejected(self):
        cases=[(1,['schema'],'mckernel.serial-operation-head.v1'),(1,['no_intervening_operation'],True),
               (1,['no_unlisted_intervening_operation'],False),(1,['physical_prerequisites'],[]),
               (1,['consumed_nonces'],['native']),(1,['consumed_nonces'],['native','grow','new']),
               (3,['backing_identity','inode'],2),(4,['actual_backing_identity','size'],110*2**30),
               (4,['clock','wall'],102),(6,['growth','kind'],'other'),(6,['growth','container'],'fake'),
               (6,['growth','after','inode'],2),(6,['growth','before','size'],142*2**30),
               (6,['grant','lower_reserves'],True),(6,['execution_review','implementation_ownership'],True),
               (6,['actual_commands','returncodes'],[1]),(6,['actual_commands','argv'],[['different']]),
               (6,['normal_fd_release','fd_closed'],False),(6,['normal_fd_release','group_absent'],False),
               (6,['fresh_physical_acceptance','observed_wall'],101),
               (6,['fresh_physical_acceptance','implementation_ownership'],True)]
        for index,path,value in cases:
            f=copy.deepcopy(self.fixture());target=f[index]
            for key in path[:-1]:target=target[key]
            target[path[-1]]=value
            with self.subTest(path=path),self.assertRaises((ValueError,KeyError)):self.call(f)
    def test_owner_only_exact_size_message_and_executing_path_change(self):
        old=OLD.read_text();new=(D/'daemon_sdk_owner.142G-SOURCE-ONLY.py').read_text()
        expected=old.replace('meta.st_size == 110 * 2**30','meta.st_size == 142 * 2**30').replace('exact unchanged110GiB root-owned backing inode/size/owner required','exact accepted142GiB root-owned backing inode/size/owner required').replace("RUNTIME_SOURCE_PATHS['scripts/native_running_external_modules_owner.py'] = '"+str(OLD)+"'", "RUNTIME_SOURCE_PATHS['scripts/native_running_external_modules_owner.py'] = '"+str(D/'daemon_sdk_owner.142G-SOURCE-ONLY.py')+"'")
        self.assertEqual(new,expected)
        self.assertEqual(hashlib.sha256(OLD.read_bytes()).hexdigest(),'94d8d3fd6e2b1181c1ea9a3b53d7d3dbaad00140c4fa8335310e75808456c750')
    def test_unmodified_adapter_apis_and_seven_commands(self):
        old=ast.parse((P/'sdk7_authority_adapter.CURRENT-WINDOW.SOURCE-ONLY.py').read_bytes())
        new=ast.parse((D/'sdk7_authority_adapter.142G-SOURCE-ONLY.py').read_bytes())
        functions=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
        a,b=functions(old),functions(new);self.assertEqual(set(a),set(b))
        changed={'context','adapt','validate_query_release','readonly_query'}
        self.assertEqual({k:a[k] for k in a if k not in changed},{k:b[k] for k in b if k not in changed})
        for name in changed:self.assertNotEqual(a[name],b[name])
    def test_current_map_replaces_only_owner_and_requires_new_publication_review(self):
        import sys
        sys.path.insert(0,str(P))
        from prepare_current_window_bindings import ORIGIN
        origin=json.loads(ORIGIN.read_bytes());old=json.loads(Path(origin['full11_map']['path']).read_bytes())
        mapping=json.loads((D/'CURRENT-CONSUMER-SOURCE-MAP.NOT-REVIEWED.json').read_bytes())
        expected=dict(old['source_sha256']);expected[g.OWNER_KEY]=hashlib.sha256((D/'daemon_sdk_owner.142G-SOURCE-ONLY.py').read_bytes()).hexdigest()
        self.assertEqual(mapping['source_sha256'],expected)
        oldpath=dict(old['effective_runtime_paths']);oldpath[g.OWNER_KEY]=str(D/'daemon_sdk_owner.142G-SOURCE-ONLY.py')
        self.assertEqual(mapping['effective_runtime_paths'],oldpath)
        bundle={k:ref(k) for k in ('current_source_map','current_source_publication','current_source_review')}
        def actual_ref(path):
            raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        bindings=dict(current_growth_validator=actual_ref(D/'growth_successor.py'),
                      current_owner=actual_ref(D/'daemon_sdk_owner.142G-SOURCE-ONLY.py'),
                      current_source_map=bundle['current_source_map'],current_adapter=ref('adapter'),
                      historical_owner=origin['owner'],historical_source_approval=origin['source_approval'])
        publication=dict(status='PASS_ACTUAL_FETCHED_CURRENT_CONSUMER_SOURCE',bindings=bindings,execution_authority=False)
        review=dict(decision='PASS_SOURCE',implementation_ownership=False,reviewer='independent',execution_authority=False,SDK_execution_released=False,source_sha256=expected,bindings=bindings,current_source_publication=bundle['current_source_publication'])
        docs=dict(current_source_map=mapping,current_source_publication=publication,current_source_review=review)
        load=lambda r:docs[r['path']]
        g.current_sources(bundle,origin,old,load,ref('adapter'))
        self.assertIn('current_growth_validator',bindings)
        review['source_sha256']=old['source_sha256']
        with self.assertRaisesRegex(ValueError,'independent current'):g.current_sources(bundle,origin,old,load,ref('adapter'))

    def test_current_adapter_end_to_end_keeps_historical_and_current_maps_separate(self):
        import importlib.util
        import sys
        spec=importlib.util.spec_from_file_location('selected_142g_adapter',D/'sdk7_authority_adapter.142G-SOURCE-ONLY.py')
        adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
        oldtests=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/parallel-m15-sdk-queue-1/test_sdk7_authority_adapter.py')
        spec=importlib.util.spec_from_file_location('retained_fixture',oldtests)
        # Import its retained module without running any parent workload/test.
        sys.path.insert(0,str(oldtests.parent))
        tm=importlib.util.module_from_spec(spec);spec.loader.exec_module(tm);tm.a=adapter
        cls=tm.AdapterTests
        cls.origin=json.loads(adapter.ORIGIN.read_bytes());cls.window=adapter.load_window()
        cls.original=adapter.bound(cls.origin['request']);cls.mapping=adapter.bound(cls.origin['full11_map'])
        cls.review=adapter.bound(cls.origin['source_approval']);cls.base=adapter.bound(cls.origin['pending_release_base'])
        obj=cls();obj.setUp()
        bundle=obj.b;native=bundle['latest_operation'];native['sha256']=g.NATIVE2_SHA
        latest=obj.doc('latest_operation');live=obj.doc('live_observation');request=obj.doc('request')
        gf=self.fixture();grow=gf[-1]['growth'];grow['previous_serial_operation']=native;grow['boot_id']=obj.w['boot_id']
        grow['closed_wall']=live['clock']['wall']-2
        growref=ref('growth');bundle['growth_closure']=growref
        gd=gf[-1];binding=dict(source=ref('source'),previous_serial_operation=native,nonce='grow',before=g.BEFORE,after=g.AFTER)
        gd['grant']['bindings']=binding;gd['execution_review']['bindings']=binding
        gd['normal_fd_release']['closed_wall']=grow['closed_wall']
        gd['fresh_physical_acceptance']['observed_wall']=live['clock']['wall']-1
        gd['fresh_physical_acceptance']['bindings']=dict(binding,**{k:ref(k) for k in ('grant','execution_review','actual_commands','normal_fd_release')})
        obj.docs.update(gd)
        head=obj.doc('operation_head');head.clear();head.update(schema='mckernel.serial-operation-head.v2',latest_container_operation=native,latest_serial_operation=growref,physical_prerequisites=[growref],no_unlisted_intervening_operation=True,consumed_nonces=[latest['nonce'],'grow'])
        request['backing_identity']={k:v for k,v in g.AFTER.items() if k!='uuid'}
        live.update(actual_backing_identity=g.AFTER,growth_closure=growref,latest_serial_operation=growref)
        def actual_ref(path):
            raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        current=json.loads((D/'CURRENT-CONSUMER-SOURCE-MAP.NOT-REVIEWED.json').read_bytes())
        for k in ('current_source_map','current_source_review','current_source_publication'):bundle[k]=ref(k)
        bindings=dict(current_growth_validator=actual_ref(D/'growth_successor.py'),current_owner=actual_ref(D/'daemon_sdk_owner.142G-SOURCE-ONLY.py'),current_source_map=bundle['current_source_map'],current_adapter=actual_ref(D/'sdk7_authority_adapter.142G-SOURCE-ONLY.py'),historical_owner=obj.o['owner'],historical_source_approval=obj.o['source_approval'])
        obj.docs['current_source_map']=current
        obj.docs['current_source_publication']=dict(status='PASS_ACTUAL_FETCHED_CURRENT_CONSUMER_SOURCE',bindings=bindings,execution_authority=False)
        obj.docs['current_source_review']=dict(decision='PASS_SOURCE',implementation_ownership=False,reviewer='independent',execution_authority=False,SDK_execution_released=False,source_sha256=current['source_sha256'],bindings=bindings,current_source_publication=bundle['current_source_publication'])
        review=obj.doc('root_admission_review')
        review.update({k:bundle[k] for k in ('current_source_map','current_source_review','current_source_publication','growth_closure')})
        obj.doc('query').update(current_owner=bindings['current_owner'],**{k:bundle[k] for k in ('current_source_map','current_source_review','current_source_publication')})
        obj.docs[obj.o['full11_map']['path']]=obj.mapping
        def load(r,*_):return obj.docs[r['path']]
        result=adapter.adapt(bundle,obj.o,obj.w,obj.now,load=load,check_history=lambda *_:(obj.mapping,obj.review))
        self.assertEqual(result['source_sha256'],current['source_sha256'])
        self.assertEqual(result['source_review'],bundle['current_source_review'])
        self.assertEqual(result['historical_source_review'],obj.o['source_approval'])
        self.assertEqual(result['physical_prerequisites'],[growref])
        self.assertFalse(result['execution_release'])
        obj.docs['current_source_review']['source_sha256']=obj.mapping['source_sha256']
        with self.assertRaisesRegex(ValueError,'independent current'):adapter.adapt(bundle,obj.o,obj.w,obj.now,load=load,check_history=lambda *_:(obj.mapping,obj.review))

if __name__=='__main__':unittest.main(verbosity=2)
