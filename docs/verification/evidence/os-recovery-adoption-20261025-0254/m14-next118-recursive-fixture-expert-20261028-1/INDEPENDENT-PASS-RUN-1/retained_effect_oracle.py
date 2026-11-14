"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite authenticated retained query/effect oracle. No actual effects are executable.
"""
from pathlib import Path
import ast
import hashlib
import json

E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
CAPTURE=E/'current116-actual-postjoin-current60-source-20261028-1/ACTUAL-POSTJOIN-OBSERVATION-2-CPU0.json'
NATIVE=E/'f05-v2-root-export-and-native-preparation-source-1/root-adopted-native-entry-4/independent-postjoin-review-1/REVIEW.json'
INHERITED111=E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2/INDEPENDENT-POSTBUILD-CURRENT-FREE.json'
MOUNT=E/'ROOT-NEW18H-KEEPER-SUCCESSOR-PREPARATION-2/ROOT-ACTUAL-POSTJOIN-CURRENT-PHYSICAL.json'


def reference(path):
    path=Path(path);raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def query(argv):
    """Only retained read-only Docker query argv enter the finite table."""
    if not isinstance(argv,list) or len(argv)<5:return False
    if argv[0] not in ['sudo','/usr/bin/sudo'] or argv[1]!='-A' or argv[2] not in ['docker','/usr/bin/docker'] or argv[3]!='--host=unix:///var/run/docker.sock':return False
    tail=argv[4:]
    if len(tail)==2 and tail[0]=='inspect':return len(tail[1])==64
    # All exact retained ps spellings are read-only, including the unfiltered
    # stopped-container census. Dispatch still requires a complete table key;
    # no option combination or blank response is synthesized here.
    return bool(tail) and tail[0]=='ps'


class RetainedEffectOracle:
    def __init__(self,source_chain):
        self.rows={};self.provenance={};self.inputs={};self.conflicts=[]
        capture=self.authenticate(reference(CAPTURE),'ebbd745f00e17f52fb2e4f589633ca74c9e64e44a643f875c6d9697dc7c9a270')
        self.capacity=capture['historical_Root59_native_and_physical']['capacity']
        self.cgroup=capture['historical_Root59_native_and_physical']['cgroup']
        self.memory=capture['historical_Root59_native_and_physical']['memory']
        self.collect(capture,self.inputs[str(CAPTURE)],'')
        # Complete the retained source-declared receipt set before dispatch. This
        # is bounded by the exact eight-source physical dependency chain, never
        # by an inventory of the repository or a missing-command retry loop.
        declared={}
        for path,row in source_chain.items():
            assert reference(path)==row
            for node in ast.walk(ast.parse(Path(path).read_bytes())):
                if not isinstance(node,ast.Dict):continue
                try:value=ast.literal_eval(node)
                except (ValueError,TypeError):continue
                if isinstance(value,dict) and set(value)=={'path','bytes','sha256'} and str(value['path']).endswith('.json'):
                    declared[value['path']]=value
        assert len(declared)<=192,'bounded physical-history receipt set exceeded'
        # These two bare Path declarations are authenticated by literal hashes
        # inside unchanged Root48.observe rather than literal BYTE dictionaries.
        declared[str(NATIVE)]=dict(reference(NATIVE),sha256='bf19e5a464ce05f49657acce7e598ce1125d8bf913c85631d5883190290e4890')
        declared[str(INHERITED111)]=dict(reference(INHERITED111),sha256='9904aa3c39b0a83d8675a77b97631f3731f2f3e568c5fde65b6ef91c28f64d19')
        for path,row in sorted(declared.items()):
            value=self.authenticate(row)
            self.collect(value,row,'')
            self.terminals(value,row,'')
        self.mount_input=reference(MOUNT)
        self.mount=self.authenticate(self.mount_input,'550b5ea0869996edfc752258a75a2414e4466bfa7338a615d3b4aa1068b93b22')['mount']

    def authenticate(self,row,sha=None):
        actual=reference(row['path'])
        assert actual==row and (sha is None or actual['sha256']==sha),'retained input drift: '+row['path']
        assert actual['bytes']<=32*2**20
        self.inputs[row['path']]=row
        return json.loads(Path(row['path']).read_bytes())

    def add(self,argv,row,source,pointer,derived=False):
        if not query(argv):return
        assert type(row['returncode'])is int and isinstance(row['stdout'],str) and isinstance(row['stderr'],str)
        response={k:row[k] for k in ['returncode','stdout','stderr']}
        # The only alias is the observed sudo executable spelling. Command args,
        # daemon URI, filters and complete response bytes stay exact.
        variants=[argv]
        alias=list(argv);alias[0]='/usr/bin/sudo' if argv[0]=='sudo' else 'sudo';variants.append(alias)
        for variant in variants:
            key=tuple(variant)
            if key in self.rows and self.rows[key]!=response:
                self.conflicts.append(dict(argv=variant,retained=self.provenance[key],other=dict(input=source,pointer=pointer),derived=derived))
                # Exact observed command replies outrank structural terminal
                # projections; the genuine latest capture remains first priority.
                if derived or not self.provenance[key]['derived']:continue
            self.rows[key]=response
            self.provenance[key]=dict(input=source,pointer=pointer,derived=derived,sudo_spelling_alias=variant!=argv)

    def collect(self,value,source,pointer):
        if isinstance(value,dict):
            if all(k in value for k in ['argv','returncode','stdout','stderr']) and isinstance(value['stdout'],str) and isinstance(value['stderr'],str):
                self.add(value['argv'],value,source,pointer)
            for key,child in value.items():self.collect(child,source,pointer+'/'+str(key))
        elif isinstance(value,list):
            for index,child in enumerate(value):self.collect(child,source,pointer+'/'+str(index))

    def terminals(self,value,source,pointer):
        if isinstance(value,dict):
            row=value.get('container_terminal')
            if isinstance(row,dict) and set(row)=={'path','bytes','sha256'} and 'retained_stopped_container' in value:
                terminal=self.authenticate(row)
                assert terminal['container']==value['retained_stopped_container']
                state=terminal['state'];assert state['Running']is False and state['Pid']==0
                argv=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect',terminal['container']]
                reply=dict(returncode=0,stdout=json.dumps([dict(Id=terminal['container'],State=state)]),stderr='')
                self.add(argv,reply,row,'/container+state',derived=True)
            for key,child in value.items():self.terminals(child,source,pointer+'/'+str(key))
        elif isinstance(value,list):
            for index,child in enumerate(value):self.terminals(child,source,pointer+'/'+str(index))

    def get(self,argv):
        try:return self.rows[tuple(argv)]
        except KeyError:raise AssertionError('UNSUPPORTED_RETAINED_EFFECT_ARGV '+json.dumps(argv))

    def manifest(self):
        rows=[]
        for argv in sorted(self.rows):
            response=self.rows[argv]
            rows.append(dict(argv=list(argv),response=response,provenance=self.provenance[argv]))
        return dict(scope=__doc__.splitlines()[0],decision='FINITE_AUTHENTICATED_RETAINED_EFFECT_ORACLE_SOURCE_ONLY',
                    inputs=list(self.inputs.values()),rows=rows,conflicts=self.conflicts,
                    aliases='Only sudo versus /usr/bin/sudo; all remaining argv unchanged',
                    terminal_projection='Only authenticated retained_stopped_container/container_terminal Id+State',
                    unsupported_commands_refuse=True,actual_commands=0,runtime_authority=None)
