import ast,json
from pathlib import Path
p=Path(__file__).resolve().parent
for f in [p/"cleanup_failed_image.py",p/"check_entry_guard_bodies.py"]:ast.parse(f.read_bytes(),filename=str(f))
print(json.dumps({"syntax_files":2,"effects":0}))
