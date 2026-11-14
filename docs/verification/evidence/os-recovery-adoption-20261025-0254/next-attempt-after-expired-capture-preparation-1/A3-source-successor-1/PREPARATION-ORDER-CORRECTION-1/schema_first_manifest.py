"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read final schema before producing a separate manifest DATA successor. Never edits
the frozen package; unchanged rows are retained without another artifact hash loop.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json

def ref(path):
    path=Path(path);raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def corrected_manifest(package):
    package=Path(package).resolve(strict=True)
    schema_path=package/'OBSERVER-SCHEMA.CURRENT63-CURRENT118.SOURCE-ONLY.json'
    schema=json.loads(schema_path.read_bytes())
    # Producer order: final observer -> schema rebind/write -> snapshot schema ->
    # manifest. Refuse a prefinal schema instead of propagating its old observer.
    if schema['observer']!=ref(package/'observe_current63_current118.py'):
        raise ValueError('finalize observer and rebind schema BEFORE manifest')
    final_schema=ref(schema_path)
    manifest_path=package/'cohort/PREPARATION-MANIFEST.json'
    previous=json.loads(manifest_path.read_bytes());successor=copy.deepcopy(previous)
    indexes=[i for i,row in enumerate(previous['external_inputs'])if row['path']==str(schema_path)]
    if len(indexes)!=1:raise ValueError('one exact observer-schema external input required')
    index=indexes[0];successor['external_inputs'][index]=final_schema
    return successor,dict(previous_manifest=ref(manifest_path),schema_external_index=index,
                          previous_schema=previous['external_inputs'][index],
                          final_schema=final_schema,other_rows_preserved=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();value,delta=corrected_manifest(args.package)
    # Separate additive DATA only. Never replace a frozen package manifest/schema.
    if args.output.resolve()==(args.package/'cohort/PREPARATION-MANIFEST.json').resolve():
        raise ValueError('frozen manifest cannot be the output')
    with args.output.open('x')as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(status='SCHEMA_FINAL_SEPARATE_MANIFEST_DATA_ONLY',output=ref(args.output),delta=delta)))

if __name__=='__main__':main()
