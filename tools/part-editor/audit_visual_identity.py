"""Audit a ReadVisualDatabase export without reading player/account data."""
import argparse
import hashlib
import json
from pathlib import Path


def audit(data, known, resources):
    items = {int(row['id']): row for row in data['item_template']}
    parts = {int(row['id']): row for row in data['part']}
    mappings = {table: {int(row['id_temp']): row for row in data[table]}
                for table in ('cai_trang', 'mini_pet')}
    report = {'counts': {table: len(data[table]) for table in
              ('item_template', 'cai_trang', 'mini_pet', 'part')},
              'missing_costumes': [], 'missing_mini_pets': [],
              'wrong_part_slots': [], 'inactive_foreign_mappings': [],
              'missing_images': [], 'source_matches': 0, 'source_differences': []}
    expected_types = {'cai_trang': (5,), 'mini_pet': (18, 21)}
    image_users = {}
    for item_id, item in items.items():
        kind = int(item['TYPE'])
        table = 'cai_trang' if kind == 5 else 'mini_pet' if kind in (18, 21) else None
        if table is None:
            continue
        mapping = mappings[table].get(item_id)
        slots = [int(mapping[key]) if mapping else -1 for key in ('head', 'body', 'leg')]
        template_part = int(item['part'])
        if kind == 5 and template_part > 0 and template_part in parts:
            slot = int(parts[template_part]['TYPE'])
            if slot in (0, 1, 2) and slots[slot] < 0:
                slots[slot] = template_part
        if (kind == 5 and all(part < 0 for part in slots)) or (
                kind in (18, 21) and any(part < 0 for part in slots)):
            report['missing_costumes' if kind == 5 else 'missing_mini_pets'].append(
                {'id': item_id, 'name': item['NAME']})
        for slot, part_id in enumerate(slots):
            if part_id < 0:
                continue
            part = parts.get(part_id)
            if part is None or int(part['TYPE']) != slot:
                report['wrong_part_slots'].append({'item': item_id, 'slot': slot, 'part': part_id})
                continue
            for frame in json.loads(part['DATA']):
                if frame and frame[0] > 0:
                    image_users.setdefault(frame[0], set()).add(item_id)
    for table, rows in mappings.items():
        for item_id in rows:
            if item_id not in items or int(items[item_id]['TYPE']) not in expected_types[table]:
                report['inactive_foreign_mappings'].append({'table': table, 'item': item_id})
    if resources:
        for image_id, users in sorted(image_users.items()):
            missing = [zoom for zoom in range(1, 5)
                       if not (resources / str(zoom) / 'icon' / f'{image_id}.png').is_file()]
            if missing:
                report['missing_images'].append({'image': image_id, 'zooms': missing, 'items': sorted(users)})
    references = {row['id']: row for row in known}
    links = {(int(row['item_id']), int(row['source_item_id']))
             for row in data['admin_catalog_item_source']
             if row['source_server'] == 'dragon14.teamobi.com:18001'}
    links.update((item_id, item_id) for item_id in items if item_id in references)
    for item_id, source_id in sorted(links):
        item, ref = items.get(item_id), references.get(source_id)
        if not item or not ref:
            continue
        # Require the whole identity; matching only a numeric ID is unsafe.
        if (item['NAME'], int(item['gender']), int(item['icon_id'])) != (
                ref['name'], ref['gender'], ref['icon_id']):
            continue
        if int(item['TYPE']) != ref['type'] and not (
                int(item['TYPE']) in (18, 21) and ref['type'] in (18, 21)):
            continue
        table = 'cai_trang' if int(item['TYPE']) == 5 else 'mini_pet'
        actual = mappings[table].get(item_id)
        differences = []
        for key in ('head', 'body', 'leg'):
            expected = ref.get(key)
            part_id = int(actual[key]) if actual else -1
            if not expected:
                if part_id >= 0:
                    differences.append(key)
                continue
            part = parts.get(part_id)
            payload = json.dumps([int(part['TYPE']), json.loads(part['DATA'])], separators=(',', ':')) if part else ''
            if hashlib.sha256(payload.encode()).hexdigest()[:32] != expected[1]:
                differences.append(key)
        if differences:
            report['source_differences'].append({'item': item_id, 'source': source_id, 'slots': differences})
        else:
            report['source_matches'] += 1
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export', type=Path)
    parser.add_argument('--known', type=Path, default=Path(__file__).resolve().parents[1] / 'clone-server/known-costume-parts.json')
    parser.add_argument('--resources', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.export.read_text(encoding='utf8')),
                   json.loads(args.known.read_text(encoding='utf8')), args.resources)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({key: len(value) if isinstance(value, list) else value
                      for key, value in result.items()}, ensure_ascii=False))
