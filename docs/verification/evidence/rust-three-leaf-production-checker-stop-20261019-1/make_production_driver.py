"""Compose only the admitted adapter delta; does not build, materialize or run."""
from pathlib import Path
import ast, hashlib, json
O = Path(__file__).resolve().parent
binding = json.loads((O / 'source-binding.json').read_text())
base = Path(binding['base_accepted_driver']['path'])
assert hashlib.sha256(base.read_bytes()).hexdigest() == binding['base_accepted_driver']['sha256']
ext = (O / 'production-driver-extension.py').read_text()
inputs = json.loads((O / 'production-commands-INPUTS.json').read_text())
assert hashlib.sha256(ext.encode()).hexdigest() == inputs['driver_extension']['sha256']
text = base.read_text()
anchor = '                _validate_release_fp_regs_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)'
assert text.count(anchor) == 1 and text.count('\ndef main(argv=None):') == 1
text = text.replace(anchor, anchor + '\n                _validate_release_tid_production(source_root, build, tools, evidence, env, stdout, stderr, timeout, command_rows)', 1)
text = text.replace('\ndef main(argv=None):', '\n' + ext + '\ndef main(argv=None):', 1)
ast.parse(text)
out = O / 'composed-adapters'
out.mkdir(exist_ok=False)
(out / base.name).write_text(text)
# This is the adapter's existing provenance dependency, not a new source tree.
provenance = base.with_name('native_rust_exact_build_offline.py')
(out / provenance.name).write_bytes(provenance.read_bytes())
print(json.dumps({'status':'COMPOSED_ONLY_NOT_EXECUTED','driver_sha256':hashlib.sha256(text.encode()).hexdigest(),'files':2}))
