"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Publication-only loader input collector. No import/execute of a runtime consumer.

A BYTE subject is not an instruction to open references contained in its payload.
Only the finite loader roles below introduce dependencies. In particular accepted
profiles, plans, source maps, captures and protected-file snapshots remain opaque.
The actual runtime authenticators and all their acceptance predicates are unchanged.
"""
from pathlib import Path
import ast
import hashlib
import json

REPO=Path('/home/holden/mckernel')
E=REPO/'docs/verification/evidence/os-recovery-adoption-20261025-0254'
MAX_METADATA=1<<20
CONTROL=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1/restart-20261028-1200-pacific-1')
LIVE_CONTROL_READS=[str(CONTROL/'armed-controller/journal.json'),str(CONTROL/'armed-controller/bridge-start.json'),
                    '/home/holden/mckernel/.git/os-autopilot/state.json',
                    '/home/holden/mckernel/.git/os-autopilot/watcher.json']


def need(ok,why):
    if not ok:raise ValueError(why)


def byte_ref(row):
    return (type(row)is dict and set(row)=={'path','bytes','sha256'} and
            type(row['path'])is str and Path(row['path']).is_absolute() and
            type(row['bytes'])is int and row['bytes']>=0 and
            type(row['sha256'])is str and len(row['sha256'])==64 and
            all(c in '0123456789abcdef'for c in row['sha256']))


def ref(path):
    path=Path(path);raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def refs(value):
    if byte_ref(value):yield value
    elif type(value)is dict:
        for child in value.values():yield from refs(child)
    elif type(value)is list:
        for child in value:yield from refs(child)


def strict(raw):
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,'duplicate JSON key');result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
                      parse_constant=lambda value:(_ for _ in ()).throw(ValueError('nonfinite JSON')))


class Closure:
    def __init__(self,read_bytes=None):
        self.read_bytes=read_bytes or(lambda path:Path(path).read_bytes())
        self.rows={};self.roles={};self.documents={};self.expanded=set();self.sources=set()

    def add(self,row,role):
        need(byte_ref(row),'exact complete publication BYTE ref: '+role)
        path=row['path']
        need(path not in self.rows or self.rows[path]==row,'conflicting loader input: '+path)
        self.rows[path]=row;self.roles.setdefault(path,set()).add(role)
        return row

    def document(self,row,role):
        self.add(row,role);path=row['path']
        if path not in self.documents:
            need(row['bytes']<=MAX_METADATA,'explicit loader metadata exceeds1MiB: '+role)
            raw=self.read_bytes(path)
            need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],
                 'changed/missing required loader metadata: '+path)
            self.documents[path]=strict(raw)
        return self.documents[path]

    def leaves(self,value,role):
        for row in refs(value):self.add(row,role)

    def selected_evidence(self,row,role):
        """Only fields read by retained observer/receipt validators, never provenance.
        Embedded owner/protected/source bytes are validated within their parent
        evidence and are deliberately not interpreted as current filesystem refs.
        """
        self.add(row,role)
        # Large accepted observation/snapshot bytes are leaf payloads. Current
        # capture receipts are obtained from the authenticated independent free.
        if not row['path'].endswith('.json') or row['bytes']>MAX_METADATA:return
        if row['path'] in self.expanded:return
        self.expanded.add(row['path']);value=self.document(row,role)
        if type(value)is not dict:return
        # These exact named fields are checked/read by Root61/60/common/physical
        # retained validators, or by successful/failed retirement/client parsers.
        recursive=['prior_ledger_retained','latest_native_once_join','latest_native_caller_join',
                   'additional_HOSTbody2_qualification_supplement','runner_join','local_terminal',
                   'holder_tool_result','container_terminal','current_observation','join',
                   'capture_positive_join','parent_join','command_receipts','raw_new_query_receipts']
        for key in recursive:
            if key in value:
                for child in refs(value[key]):self.selected_evidence(child,role+'/'+key)
        for key in ['stdout','stderr','raw','attempt_started','release','source_executor','proofs']:
            if key in value:self.leaves(value[key],role+'/'+key)
        # Raw captures, their embedded physical history, protected/source maps,
        # profiles, plans and embedded command payloads are byte subjects only.
        if 'actual_postjoin_observation'in value:self.leaves(value['actual_postjoin_observation'],role+'/accepted_capture')
        for op in value.get('ordinary_operations_since_prior_heavy_boundary',[]):
            for key in ['grant','consumed_claim','actual_results','results','actual_whole_join','join','actual_tool']:
                if key in op:
                    for child in refs(op[key]):self.selected_evidence(child,role+'/ordinary/'+key)
        for actor in value.get('actors',[]):
            if type(actor)is dict and 'evidence'in actor:self.leaves(actor['evidence'],role+'/actor_evidence')
        for name in ['RETAINED-OWNER-SNAPSHOT.json','RETAINED-OWNER-AND-GUEST-SNAPSHOT.json']:
            if name in value.get('evidence',{}):self.add(value['evidence'][name],role+'/embedded_snapshot')
        # The two recorded failed BFD attempts explicitly authenticate their
        # original JOIN/raw files, rather than the command's embedded provenance.
        if value.get('decision')=='ACTUAL_SECOND_RETIREMENT_ATTEMPT_FAILED_IN_PREINSPECT_BEFORE_REMOVAL':
            for command in value['commands']:
                for child in command['files']:self.selected_evidence(child,role+'/failed2_command')

    def source(self,row,role):
        """Read literal BYTE declarations in the selected retained reader sources.
        This does not import them or inspect repository directories/artifacts.
        """
        self.add(row,role)
        if row['path']in self.sources:return
        self.sources.add(row['path']);raw=self.read_bytes(row['path'])
        need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],
             'selected loader source drift: '+row['path'])
        for node in ast.walk(ast.parse(raw)):
            if not isinstance(node,ast.Dict):continue
            try:value=ast.literal_eval(node)
            except(ValueError,TypeError):continue
            if not byte_ref(value):continue
            if value['path'].endswith('.py'):
                # Retained validators contain BYTE loader edges; current guard
                # subjects remain opaque and do not introduce historical guards.
                name=Path(value['path']).name
                if name.startswith('observe_')or name=='check_postnative_current_new12h.py':self.source(value,role+'/reader')
                else:self.add(value,role+'/source_subject')
            elif value['path'].endswith('.json'):self.selected_evidence(value,role+'/literal_DATA')
            else:self.add(value,role+'/literal_BYTE')

    def control(self,row,role):
        value=self.document(row,role)
        self.leaves(value,role+'/authenticated_subject')
        return value

    def result(self):
        result=[]
        for path,row in sorted(self.rows.items()):
            try:fetched=str(Path(path).relative_to(REPO))
            except ValueError:fetched=None
            result.append(dict(actual=row,fetched_equivalent_path=fetched,
                               requires_explicit_fetched_alias=fetched is None,
                               declared_by=sorted(self.roles[path]),
                               kind='JSON'if path.endswith('.json')else'BYTE',
                               payload_references_recursively_followed=False))
        return result


def runtime_data_rows(binding_ref,selection_ref,operation_ref,read_bytes=None):
    c=Closure(read_bytes)
    binding=c.control(binding_ref,'typed118');selection=c.control(selection_ref,'upstream_selection')
    current=c.control(binding['accepted_current_bindings'],'accepted_current63')
    subjects=c.control(selection['subject_map'],'upstream_subjects')
    pins=c.control(selection['inputs'],'upstream_INPUTS')
    c.control(binding['current_boundary'],'typed118_descriptor')
    c.control(binding['readonly_release'],'typed118_readonly_release')
    ledger=c.document(current['ledger'],'current63_ledger')
    # Immutable window is actually loaded by both current shared guards. This is
    # a fetched byte comparison, never a substitute for live account/controller IO.
    c.document(ledger['actual_window'],'actual_immutable_window')
    c.selected_evidence(current['latest_free'],'accepted_current63_free')
    for key in ['pending_ledger','retirement_result','retirement_parent_join']:
        c.selected_evidence(current[key],'current63_'+key)
    operation=c.control(operation_ref,'operation118_binding')
    c.control(operation['successor'],'operation118_successor')
    c.document(operation['independent_review'],'operation118_review')
    base=Path(selection['observer']['path']).parent
    history={}
    for name in ['ROOT61-RUNTIME-DEPENDENCIES.json','ACTUAL-PINS.json','ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json']:
        history[name]=c.control(ref(base/'history'/name),'implicit_history:'+name)
    common=history['ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json']
    physical=c.control(common['physical_history_configuration'],'physical_configuration')
    config=c.control(current['guard_configuration'],'upstream_current_guard_configuration')
    c.control(config['successor'],'upstream_current_operation')
    c.document(config['review'],'upstream_current_operation_review')
    need(history['ROOT61-RUNTIME-DEPENDENCIES.json']['guard_configuration']==current['guard_configuration']
         and common['account_window_guard_configuration']==current['guard_configuration']
         and physical['guard_config']==current['guard_configuration'],
         'all recursive current guard config bindings agree')
    # INPUTS and implicit current60 pins declare byte subjects. Only the genuine
    # runtime metadata roles read by validators are expanded below.
    for key,row in pins.items():
        if byte_ref(row)and row['path'].endswith('.json')and key not in ['retirement_requirements','retirement_packet','retirement_bindings']:
            c.selected_evidence(row,'upstream_INPUTS/'+key)
    for key,row in history['ACTUAL-PINS.json'].items():
        if byte_ref(row)and row['path'].endswith('.json')and key not in ['plan','profile','operation_binding','common_dependencies']:
            c.selected_evidence(row,'current60/'+key)
    draft=c.document(pins['ledger_draft'],'BFD_ledger_draft')
    for key in ['worker_result','profile','plan']:c.add(draft['bfd_default_build'][key],'BFD_retained_'+key)
    rb=c.control(pins['retirement_bindings'],'retirement_executor_BINDINGS')
    packet=c.document(rb['packet'],'retirement_packet')
    c.leaves(packet['source_refs'],'retirement_packet/source_refs_authenticated_as_BYTES')
    protected=c.document(rb['protected'],'protected_originals_opaque_files')
    c.leaves(protected['failed_source_evidence'],'protected_originals/failed_source_evidence')
    for row in rb['actor_evidence']:c.selected_evidence(row,'retirement_actor_evidence')
    # Only reader sources in the accepted source map are inspected. Neither
    # accepted source-port manifests nor protected-file lists become live edges.
    for key,row in subjects.items():
        if key.startswith(('history:','historical_physical:')):c.source(row,'selected_reader:'+key)
    c.source(pins['history_source'],'original_retained_Root61_reader')
    # Bare Path reads in unchanged Root48 and physical baseline are not literal
    # BYTE dicts. Their finite paths are explicit; no directory discovery occurs.
    bare=[E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/ROOT-ACTUAL-CURRENT-BOUNDARY.json',
          E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/finite-review-handoff-correction-source-1/ROOT-ACTUAL-CURRENT-BOUNDARY.json',
          E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/finite-review-handoff-correction-source-1/attempt4-root51-boundary-contract-correction-source-1/ROOT-ACTUAL-CURRENT-BOUNDARY.json',
          E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2/INDEPENDENT-POSTBUILD-CURRENT-FREE.json',
          E/'f05-v2-root-export-and-native-preparation-source-1/root-adopted-native-entry-4/independent-postjoin-review-1/REVIEW.json',
          E/'ROOT-NEW18H-KEEPER-SUCCESSOR-PREPARATION-2/ROOT-ACTUAL-POSTJOIN-CURRENT-PHYSICAL.json']
    for path in bare:c.selected_evidence(ref(path),'implicit_retained_reader_JSON')
    baseline=E/'ROOT-F03-F06-RUSTMM-STRICT235-NATIVE-ADMISSION-1'
    export=c.document(ref(baseline/'OWNER-RAW-EXPORT.json'),'implicit_baseline_owner_export')
    for row in export['rows']:
        c.add(dict(path=str(baseline/'OWNER-RAW'/row['relative']),bytes=row['bytes'],sha256=row['sha256']),
              'baseline_export_exact_raw_member')
    c.add(ref(baseline/'CAPTURE/JOINED.json'),'implicit_baseline_capture_join')
    c.add(ref(E/'current290-build3-postjoin-current-physical-1/check_current.py'),'implicit_physical_helper_source')
    plan=Path('/home/holden/mckernel-work/scratch/m14-current290-owner213-rolejoin-pathfix-retirement-20261026-1.plan.json')
    c.document(ref(plan),'implicit_physical_record_absence_plan')
    # Current guard predecessor is a source read, not an invocation or account snapshot.
    c.add(ref(E/'operation-account-window-new12h-source-1/actual_account_window.py'),'shared_guard_pure_account_semantics_source')
    # Exact immutable inputs hardpinned by guardian4889. Dynamic controller/account
    # records in LIVE_CONTROL_READS remain fresh runtime IO, never fetched authority.
    guardian=c.read_bytes(pins['guardian']['path'])
    need(len(guardian)==pins['guardian']['bytes'] and hashlib.sha256(guardian).hexdigest()==pins['guardian']['sha256'],
         'actual guardian source bytes')
    constants={}
    for node in ast.parse(guardian).body:
        if isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            try:constants[node.targets[0].id]=ast.literal_eval(node.value)
            except(ValueError,TypeError):pass
    c.document(constants['ARM_RECEIPT_REF'],'guardian_immutable_parent_arm_receipt')
    frozen=ref(CONTROL/'armed-controller/FROZEN-PACKET.json')
    need(frozen['sha256']==constants['PACKET_SHA'],'guardian frozen packet hardpin')
    packet=c.document(frozen,'guardian_immutable_frozen_packet')
    for name,sha in packet['private'].items():
        path=CONTROL/'armed-controller'/name
        row=dict(path=str(path),bytes=path.stat().st_size,sha256=sha)
        if name=='CONFIG.json':
            need(sha==constants['CONFIG_SHA'],'guardian CONFIG hardpin')
            c.document(row,'guardian_immutable_config')
        else:c.add(row,'guardian_immutable_private_BYTE')
    for name,sha in packet['canonical'].items():
        path=REPO/'scripts'/name
        c.add(dict(path=str(path),bytes=path.stat().st_size,sha256=sha),'guardian_canonical_BYTE')
    need(ledger['actual_window']['sha256']==constants['WINDOW_SHA'],'same hardpinned immutable window')
    return c.result()
