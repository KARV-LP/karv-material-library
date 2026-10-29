"""Reassemble the unchanged technical GLB. No dependencies: python assemble-reference.py"""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'transport.json').read_text())
chunks = []
for part in manifest['parts']:
    data = (root / part['file']).read_bytes()
    assert len(data) == part['bytes']
    assert hashlib.sha256(data).hexdigest() == part['sha256']
    chunks.append(data)
data = b''.join(chunks)
assert len(data) == manifest['bytes']
assert hashlib.sha256(data).hexdigest() == manifest['sha256']
(root / manifest['file']).write_bytes(data)
print('PASS:', manifest['file'], manifest['sha256'])
