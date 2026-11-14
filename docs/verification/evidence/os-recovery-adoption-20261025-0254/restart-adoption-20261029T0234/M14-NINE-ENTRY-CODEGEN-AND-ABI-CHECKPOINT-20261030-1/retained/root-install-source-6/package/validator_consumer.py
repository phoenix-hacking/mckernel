"""Functional McKernel data-only source preparation; no security testing."""
from dataclasses import dataclass
import base64
import hashlib
import json
import compositor


@dataclass(frozen=True)
class SourceCollection:
    """Collector-returned data only; never a source, native or execution release."""
    value: bytes


def consume(plan):
    plan.revalidate()
    compositor._accept_source_binding(plan)
    plan.revalidate()
    compositor._accept_effective_view(plan)
    plan.revalidate()
    result=compositor._collect(plan)
    if type(result) is not bytes:raise TypeError('collector must return data-only bytes')
    plan.revalidate()
    return SourceCollection(result)


# New diagnostic serialization format limit; not a collector limit.
MAX_RESULT_OUTPUT_BYTES = 2 * 1024 * 1024


def stdout_record(result,nonce):
    if type(result) is not SourceCollection or type(result.value) is not bytes:
        raise ValueError('data-only source collection required')
    if len(result.value)>MAX_RESULT_OUTPUT_BYTES:
        raise ValueError('diagnostic payload length %d exceeds output limit %d' % (len(result.value),MAX_RESULT_OUTPUT_BYTES))
    if type(nonce) is not str or len(nonce)!=64 or any(c not in '0123456789abcdef' for c in nonce):
        raise ValueError('operation nonce required')
    record={'record_type':'source_collection_result_data_v1','authority':None,
            'nonce':nonce,'payload_length':len(result.value),
            'payload_sha256':hashlib.sha256(result.value).hexdigest(),
            'payload_base64':base64.b64encode(result.value).decode('ascii')}
    raw=(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('ascii')
    if len(raw)>MAX_RESULT_OUTPUT_BYTES:
        raise ValueError('diagnostic record length %d exceeds output limit %d (payload length %d)' % (len(raw),MAX_RESULT_OUTPUT_BYTES,len(result.value)))
    return raw
