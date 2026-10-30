from pathlib import Path
import hashlib,json
base=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1')
source=base/'sdk21-nonheld13-data32-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3'
d=json.loads(Path('predecessor/f06_origin_command_profile.json').read_bytes()); q=json.loads(source.read_bytes())['commands'][2]
d['exact_commands']=[{'stage':'selected x86 syscall object','argv':q['argv'],'cwd':q['cwd'],'new_output':q['output']}]
d['composed_arch_source_sha256']=hashlib.sha256(Path('src/arch/x86_64/kernel/syscall.c').read_bytes()).hexdigest()
assert d['composed_arch_source_sha256']=='b2db4dce35ce2da311b71de284bcbf7aa739536cf1f81742aae9fd41c41b5ef9'
d['status']='SOURCE_ONLY_E6A_PROFILE_SUCCESSOR_NO_EXECUTION_RELEASE'
d['successor_e6a']={'profile_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'note':'Only source binding and exact selected arch command rebased; inherited provenance is historical, not acceptance or runtime authority.'}
p=Path('scripts/f06_origin_command_profile.json');p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');sha=hashlib.sha256(p.read_bytes()).hexdigest()
s=Path('predecessor/derive_f06_origin.py').read_text().replace('Support precisely the private CURRENT113 arch-command profile; reject profile drift.','Support precisely the private e6a arch-command profile; reject profile drift.').replace('4306a26c60fd6904c0644087d7dcfb7481b985045e216b8bec5575aafab5d418',sha)
old='''    if argv.count("-c") != 1 or argv.index("-c") != len(argv) - 2:
        raise ValueError("source token must be the one literal final -c operand")'''
new='''    if argv.count("-c") != 1 or argv[argv.index("-c")+1:-1] != [
        "-DMCKERNEL_RUST_F06_XRSTOR_LEAF",
        "-DMCKERNEL_RUST_F06_BAD_FRAME_LEAF",
        "-DMCKERNEL_RUST_F06_SIGNAL_CONTEXT",
        "-DMCKERNEL_RUST_F06_REGSET_DEFINED_DIAGNOSTIC",
        "-DMCKERNEL_RUST_F06_DO_SIGNAL_WHOLE",
        "-DMCKERNEL_RUST_F06_DEBUG_CONSTANTS",
    ]:
        raise ValueError("exact e6a flags must precede the single final source operand")'''
assert s.count(old)==1;s=s.replace(old,new);Path('scripts/derive_f06_origin.py').write_text(s)
