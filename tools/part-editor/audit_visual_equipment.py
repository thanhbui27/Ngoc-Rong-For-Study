"""Audit every wearable visual in an exported catalog, using only local resources."""
import argparse
import json
from pathlib import Path


def audit(snapshot, server):
    data = {k: [{k.lower(): v for k, v in row.items()} for row in rows] for k, rows in snapshot.items()}
    parts = {int(r['id']): r for r in data['part']}
    flags = {int(r['id']): r for r in data['flag_bag']}
    names = {r['name']: int(r['n_frame']) for r in data['img_by_name']}
    mappings = {k: {int(r['id_temp']): r for r in data[k]} for k in ['cai_trang', 'mini_pet', 'pet_follow']}
    report = {'ready': {}, 'blocked': {}, 'bad_slot_mappings': [], 'missing_named_files': [], 'missing_ready_icons': []}

    def icon(id):
        return id >= 0 and all((server / f'resources/normal/image/{z}/icon/{id}.png').is_file() for z in range(1, 5))

    def effect(id):
        # Same definition and PNG at another zoom is a valid EffectAssetResolver source.
        candidates = []
        for z in range(1, 5):
            p = server / f'Eff/effect/x{z}/data/DataEffect_{id}'
            if p.is_file():
                candidates.append((z, p.read_bytes()))
        return len(candidates) >= 2 and any((server / f'Eff/effect/x{z}/img/ImgEffect_{id}.png').is_file() for z, _ in candidates)

    def named(prefix, id):
        return all(f'{prefix}{id}_{layer}' in names and names[f'{prefix}{id}_{layer}'] > 0
                   and all((server / f'resources/ThanhBN/img_by_name/x{z}/{prefix}{id}_{layer}.png').is_file()
                           for z in range(1, 5)) for layer in [0, 1])

    for i in data['item_template']:
        id, kind, part = int(i['id']), int(i['type']), int(i['part'])
        ready = False
        category = None
        if kind == 5 or kind in [18, 21]:
            category = 'costumes' if kind == 5 else 'mini_pets'
            mapping = mappings['cai_trang' if kind == 5 else 'mini_pet'].get(id)
            slots = [int(mapping[k]) if mapping else -1 for k in ['head', 'body', 'leg']]
            if kind == 5 and part > 0 and part in parts and int(parts[part]['type']) in [0, 1, 2]:
                slot = int(parts[part]['type'])
                if slots[slot] < 0:
                    slots[slot] = part
            ready = any(s >= 0 for s in slots) if kind == 5 else all(s >= 0 for s in slots)
            for slot, pid in enumerate(slots):
                if pid < 0:
                    continue
                p = parts.get(pid)
                if p is None or int(p['type']) != slot:
                    report['bad_slot_mappings'].append({'item': id, 'part': pid, 'slot': slot})
                    ready = False
                elif any(row and row[0] > 0 and not icon(row[0]) for row in json.loads(p['data'])):
                    ready = False
        elif kind == 72:
            category = 'follow_pets'
            p = mappings['pet_follow'].get(id)
            ready = bool(p and icon(int(p['icon'])) and int(p['frame']) > 0)
        elif kind in [23, 24]:
            category = 'mounts'
            ready = named('mount_', part) if part >= 0 else id in [346, 347, 348, 349, 350, 351, 396, 532]
        elif kind in [11, 17] and id >= 467 and not 1993 <= id <= 1998:
            category = 'backs'
            f = flags.get(part)
            ready = effect(part) if part in [201, 205, 207] else bool(f and part < 201 and all(icon(int(v)) for v in f['icon_data'].split(',')))
        elif kind == 39:
            category = 'titles'
            ready = part >= 0 and effect(part)
        if category:
            report['ready' if ready else 'blocked'].setdefault(category, []).append(id)
            if ready and not icon(int(i['icon_id'])):
                report['missing_ready_icons'].append({'item': id, 'icon': int(i['icon_id']), 'category': category})
    for name in names:
        missing = [z for z in range(1, 5) if not (server / f'resources/ThanhBN/img_by_name/x{z}/{name}.png').is_file()]
        if missing:
            report['missing_named_files'].append({'name': name, 'zooms': missing})
    report['counts'] = {state: {k: len(v) for k, v in report[state].items()} for state in ['ready', 'blocked']}
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--server', type=Path, default=Path('Server'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.snapshot.read_text(encoding='utf-8')), args.server)
    args.output.write_bytes((json.dumps(result, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result['counts']))
    if result['bad_slot_mappings']:
        raise SystemExit('Wrong-slot mappings remain')
