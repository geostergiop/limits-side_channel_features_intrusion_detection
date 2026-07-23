"""Repair local malware-family labels in an existing SQLite database.

Usage:
    python repair_db_labels.py [path/to/traffic.db]
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'data' / 'traffic.db'
if not DB.exists():
    raise SystemExit(f'Database not found: {DB}')

mapping = {
    'mnt-attack-2018-03-27_win23': 'BitCoinMiner',
    'mnt-attack-2018-04-03_win10': 'TrojanDownloader',
    'mnt-attack-2018-04-03_win12': 'Website_5.8.88.175',
    'mnt-attack-2018-04-04_win16': 'Dridex',
    'mnt-attack-2021-11-29_win5': 'Hancitor',
}

conn = sqlite3.connect(DB)
cur = conn.cursor()
updated = 0
for dataset_name, family in mapping.items():
    cur.execute('UPDATE datasets SET malware_family = ? WHERE name = ?', (family, dataset_name))
    cur.execute('UPDATE sessions SET malware_family = ? WHERE dataset_id IN (SELECT id FROM datasets WHERE name = ?) AND is_malicious = 1', (family, dataset_name))
    updated += cur.rowcount >= 0
conn.commit()
print(f'Applied label repair mapping to {DB}.')
