"""Read Utage AdvImportBook rows for the final text builder."""
import json
from pathlib import Path

def read_rows(source):
    source = Path(source)
    if source.suffix != '.asset':
        with source.open(encoding='utf-8') as stream:
            return [json.loads(line) for line in stream if line.strip()]
    import UnityPy
    rows = []
    for obj in UnityPy.load(str(source)).objects:
        if obj.type.name != 'MonoBehaviour':
            continue
        data = obj.read_typetree()
        for grid, value in enumerate(data.get('importGridList', [])):
            for row in value.get('rows', []):
                strings = list(row.get('strings') or [])
                strings += [''] * max(0, 12 - len(strings))
                rows.append({'b': data['m_Name'], 'g': grid, 's': strings})
    return rows
