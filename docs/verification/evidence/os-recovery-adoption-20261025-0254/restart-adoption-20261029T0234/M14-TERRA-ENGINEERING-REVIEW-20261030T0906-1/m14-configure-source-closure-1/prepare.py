from pathlib import Path
p=Path(__file__).parent;b=p.parent
old=b/'m14-configure-sdk-v8-source-1'
d=(old/'driver.successor.py').read_text()
a="or target=='/nightly' or target.startswith('/nightly/')) and target not in expected:";z="or target=='/nightly' or target.startswith('/nightly/') or target=='/out' or target.startswith('/out/')) and target not in expected:"
assert d.count(a)==1; d=d.replace(a,z);(p/'driver.closure.py').write_text(d)
v=(old/'validator.successor.py').read_text();key='def _collect(request, profile_path, request_path, source_map_path):\n'; assert v.count(key)==1
helper='''# Source-only proposal binding; this is not an admission, snapshot or live identity.
COMPOSITE_PROPOSAL_SHA = '8cb23a435a512bff5cc8a80d28fe9c70764ef047918c60722e535fa721738593'

def _check_composite_proposal(path, mounts):
    proposal, ref = _document(path, COMPOSITE_PROPOSAL_SHA, 'ON composite source proposal')
    _require(proposal.get('status')=='SOURCE_ONLY_UNRELEASED', 'unexpected composite proposal status')
    expected=proposal.get('on_source_mount_proposal')
    _require(isinstance(expected,dict) and expected, 'ON source mounts missing')
    _mount_graph(mounts)
    source={target:host for host,target,ro in mounts if target not in ('/work','/out')}
    _require(source==expected, 'ON source mount proposal mismatch')
    return ref

'''
v=v.replace(key,helper+key);(p/'validator.closure.py').write_text(v)
