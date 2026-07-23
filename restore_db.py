"""Restore data/traffic.db from data/traffic.db.xz.

Usage:
    python restore_db.py
"""
from pathlib import Path
import lzma

base = Path(__file__).resolve().parent
src = base / 'data' / 'traffic.db.xz'
dst = base / 'data' / 'traffic.db'

if not src.exists():
    raise SystemExit(f'Missing compressed database: {src}')
if dst.exists():
    print(f'Database already exists: {dst}')
    raise SystemExit(0)

print(f'Restoring {dst} from {src} ...')
with lzma.open(src, 'rb') as fin, open(dst, 'wb') as fout:
    while True:
        chunk = fin.read(1024 * 1024)
        if not chunk:
            break
        fout.write(chunk)
print('Done.')
