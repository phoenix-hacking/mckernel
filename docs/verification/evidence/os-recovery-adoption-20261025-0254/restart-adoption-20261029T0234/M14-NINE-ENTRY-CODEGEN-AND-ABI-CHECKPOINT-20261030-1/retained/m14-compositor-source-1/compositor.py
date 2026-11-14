"""Functional McKernel OS/apps and Rust/assembly migration; no security testing.

Disabled source candidate. Authentication is delegated only to the separately
reviewed, pinned inherited-channel adapter. This module cannot launch, collect,
mount, select or release any operation and never interprets DATA as authority.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

# Both are intentionally unbound until separate review and admission.
PROFILE_SHA256 = None
ADAPTER_SOURCE_SHA256 = None
ADAPTER_SOURCE = Path(__file__).parent.parent / 'authenticated-adapter-source-1' / 'adapter.py'
CONTRACT_SHA256 = 'd4b38335f7d1af1998b9999a676ae5eee40b2b640021a144d19169328d68e0fd'
PARSER_SHA256 = '74eec517909d92d178d77771dd8ae59e826df50cd17121957a03e320b93d1c96'
COMPOSITE_SHA256 = '5aa4827ff9a66c89b27102e53f606da5527aaf317812a8b7ad53174a8840c6c2'
STATUS = 'SOURCE_ONLY_UNSELECTED_NOT_RELEASED'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _collect(*_args, **_kwargs):
    # This is a separate, additive candidate; original collector remains intact.
    raise ValueError('SOURCE_ONLY: authenticated source and effective-view release unbound')


def _accept_source_binding(*_args, **_kwargs):
    raise ValueError('SOURCE_ONLY: source binding not released')


def _accept_effective_view(*_args, **_kwargs):
    raise ValueError('SOURCE_ONLY: effective view not released')


def _read_regular(path, expected, limit=2*1024*1024):
    _require(type(expected) is str and len(expected)==64 and
             all(x in '0123456789abcdef' for x in expected), 'digest unbound')
    flags=os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd=os.open(str(path),flags)
    try:
        before=os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode) and before.st_size<=limit,'not a bounded regular source')
        data=b''
        while len(data)<=limit:
            part=os.read(fd,min(65536,limit+1-len(data)))
            if not part: break
            data+=part
        after=os.fstat(fd)
        identity=lambda st:(st.st_dev,st.st_ino,st.st_mode,st.st_uid,st.st_gid,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
        _require(len(data)<=limit and identity(before)==identity(after) and hashlib.sha256(data).hexdigest()==expected,'source changed or digest differs')
        return data
    finally:
        os.close(fd)


def _load_pinned_adapter():
    # The code is not even loaded while the source pin is unset.
    raw=_read_regular(ADAPTER_SOURCE, ADAPTER_SOURCE_SHA256)
    mod=types.ModuleType('_m14_pinned_custody_adapter')
    mod.__file__=str(ADAPTER_SOURCE)
    sys.modules[mod.__name__]=mod
    try:
        exec(compile(raw,mod.__file__,'exec'),mod.__dict__)
    finally:
        sys.modules.pop(mod.__name__,None)
    _require(getattr(mod,'CONTRACT_SHA',None)==CONTRACT_SHA256 and
             getattr(mod,'SOURCE_SHA',None)==PARSER_SHA256 and
             isinstance(getattr(mod,'CustodySession',None),type),'adapter binding differs')
    return mod


def _profile():
    # Even source planning through the channel is held until separately reviewed.
    _require(PROFILE_SHA256 is not None and ADAPTER_SOURCE_SHA256 is not None,'SOURCE_ONLY: reviewed profile and adapter are unbound')
    raw=_read_regular(Path(__file__).parent/'PROFILE.V2.SOURCE-ONLY.json',PROFILE_SHA256)
    profile=json.loads(raw)
    _require(profile.get('status')==STATUS and profile.get('authority') is None and
             profile.get('contract_sha256')==CONTRACT_SHA256 and
             profile.get('composite_sha256')==COMPOSITE_SHA256,'profile binding differs')
    return raw


def _check_graph(data, contract):
    # The adapter supplies frozen parser data. No raw JSON/caller receipt path exists.
    _require(getattr(data,'synthetic',None) is False and getattr(data,'authority','missing') is None and
             getattr(data,'status',None)=='UNAUTHENTICATED_CANDIDATE_DATA_ONLY' and
             getattr(data,'contract_sha256',None)==CONTRACT_SHA256,'adapter graph domain differs')
    mounts=data.mounts
    _require(type(mounts) is tuple and len(mounts)==16 and len(contract['mounts'])==16,'exact graph size')
    for m,expected in zip(mounts,contract['mounts']):
        _require(m.target==expected['target'] and m.access==expected['access'], 'graph target/order/access')
        _require(expected['host'] is None or m.host==expected['host'],'graph source')
        _require(expected['sha256'] is None or m.content_sha256==expected['sha256'],'graph bytes')
    _require(len(data.pre_shadow)==157,'Rust pre-shadow closure')
    _require({name: sha for name, _ident, sha in data.pre_shadow} ==
             contract['rust_parent_members'], 'Rust pre-shadow bytes')


@dataclass(frozen=True)
class SourcePlan:
    """Data view only; the attached custody session must remain open.

    This value is neither operation authority nor an accepted source/mount view.
    The original _collect and effective-view gates remain independently required.
    """
    session: object
    candidate_data: object
    profile_bytes: bytes
    authority: None = None
    status: str = STATUS

    def revalidate(self):
        _require(not self.session.closed,'custody channel closed')
        observed=self.session.revalidate()
        _require(observed==self.candidate_data,'custody graph changed')
        return observed


def prepare_from_inherited_channel(fd):
    """Return source plan with a live adapter session; never accept caller DATA.

    The adapter owns authentication semantics and is unbound pending independent
    review. Channel possession is not a workload, profile, or native release.
    """
    profile=_profile()
    _require(type(fd) is int and fd>=0,'inherited channel required')
    contract=json.loads(_read_regular(Path(__file__).parent/'GRAPH-CONTRACT.json',CONTRACT_SHA256))
    adapter=_load_pinned_adapter()
    session=adapter.CustodySession(fd)
    try:
        _require(type(session) is adapter.CustodySession and not session.closed,'adapter session absent')
        first=session.data
        _check_graph(first,contract)
        second=session.revalidate()
        _require(second==first and not session.closed,'custody revalidation differs')
        # Session ownership transfers to caller; this does not release any lease.
        return SourcePlan(session,first,profile)
    except BaseException:
        session.close()
        raise


def launch(*_args, **_kwargs):
    raise ValueError('SOURCE_ONLY: launch not released')


def release_lease(*_args, **_kwargs):
    raise ValueError('SOURCE_ONLY: lease retirement not released')
