"""Build reviewed V30 repairs from a read-only catalog export and existing assets.

Run from the repo root with --snapshot FILE. No database connection or AI artwork.
Missing costume models are deliberately left blocked. Requires Pillow.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.snapshot.read_text(encoding='utf-8'))
    data = {k: [{k.lower(): v for k, v in r.items()} for r in rows] for k, rows in raw.items()}
    items = {int(r['id']): r for r in data['item_template']}
    parts = {int(r['id']): r for r in data['part']}
    flags = {int(r['id']): r for r in data['flag_bag']}
    maps = {int(r['id_temp']): r for r in data['cai_trang']}
    assets = set()
    sql = ['-- Verified source models; same-item static accessories where animations are lost.',
           '-- Avatar-only costumes remain blocked. No character names are changed.']
    report = {'costumes': [], 'backs': [], 'mounts': [], 'titles': [], 'blocked_backs': [],
              'pet1322': {'missing_pose': 20831, 'replacement_pose': 20830}, 'assets': []}

    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    def icon_path(id, z):
        return Path(f'Server/resources/normal/image/{z}/icon/{id}.png')

    def has_icon(id):
        return all(icon_path(id, z).is_file() for z in range(1, 5))

    def valid_flag(f):
        return f and int(f['id']) < 201 and all(has_icon(int(v)) for v in f['icon_data'].split(','))

    def save_image(image, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
        assets.add(path.as_posix())

    def update_item(i, field, value):
        old = i[field]
        if str(old) == str(value):
            return
        sql.append(f'UPDATE `item_template` SET `{field}`={value} WHERE `id`={i["id"]}'
                   f' AND `TYPE`={i["type"]} AND BINARY `NAME`=BINARY {quote(i["name"])}'
                   f' AND `{field}`={old};')

    # BossData.CUMBER/CUMBER2 provide a complete, independently identified model.
    for id in [1256, 1264, 1274, 2500, 1275, 2501, 2046]:
        i = items[id]
        head = 1390 if id in [1275, 2501, 2046] else 1387
        ids = [head, 1388, 1389]
        for slot, pid in enumerate(ids):
            assert int(parts[pid]['type']) == slot
            assert all(has_icon(row[0]) for row in json.loads(parts[pid]['data']))
            assets.update(icon_path(row[0], z).as_posix()
                          for row in json.loads(parts[pid]['data']) for z in range(1, 5))
        old = maps.get(id)
        old_clause = ' AND '.join(f'c.`{k}`={old[k]}' for k in ['head', 'body', 'leg', 'bag']) if old else 'c.`id_temp` IS NULL'
        joins = ''.join(f' JOIN `part` p{slot} ON p{slot}.`id`={pid} AND p{slot}.`TYPE`={slot}'
                        f' AND SHA2(p{slot}.`DATA`,256)={quote(hashlib.sha256(parts[pid]["data"].encode()).hexdigest())}'
                        for slot, pid in enumerate(ids))
        sql.append('INSERT INTO `cai_trang` (`id_temp`,`head`,`body`,`leg`,`bag`) '
                   f'SELECT i.`id`,{head},1388,1389,-1 FROM `item_template` i{joins}'
                   f' LEFT JOIN `cai_trang` c ON c.`id_temp`=i.`id` WHERE i.`id`={id} AND i.`TYPE`=5'
                   f' AND BINARY i.`NAME`=BINARY {quote(i["name"])} AND {old_clause}'
                   ' ON DUPLICATE KEY UPDATE `head`=VALUES(`head`),`body`=VALUES(`body`),`leg`=VALUES(`leg`),`bag`=-1;')
        if not has_icon(int(i['icon_id'])):
            update_item(i, 'icon_id', 11530 if head == 1390 else 11529)
        report['costumes'].append({'item': id, 'parts': ids, 'source': 'BossData.CUMBER/CUMBER2'})
    for head, avatar in [(1387, 11529), (1390, 11530)]:
        previous = next((r for r in data['head_avatar'] if int(r['head_id']) == head), None)
        if previous:
            sql.append(f'UPDATE `head_avatar` SET `avatar_id`={avatar} WHERE `head_id`={head} AND `avatar_id`={previous["avatar_id"]};')
        else:
            sql.append(f'INSERT INTO `head_avatar` (`head_id`,`avatar_id`) SELECT {head},{avatar} WHERE NOT EXISTS (SELECT 1 FROM `head_avatar` WHERE `head_id`={head});')
        assets.update(icon_path(avatar, z).as_posix() for z in range(1, 5))

    # Copy-on-write: never change a part shared by another item.
    new_part = max(parts) + 1
    assert new_part == 2686, 'Refresh the allocation after catalog changes'
    frames = json.loads(parts[1370]['data'])
    frames[4] = frames[3].copy()
    for n in range(8, 17):
        frames[n] = frames[1].copy()  # Own neutral pose instead of a human body (image 34).
    payload = json.dumps(frames, separators=(',', ':'))
    assert all(has_icon(f[0]) for f in frames)
    sql.append(f'INSERT INTO `part` (`id`,`TYPE`,`DATA`) SELECT {new_part},1,{quote(payload)} '
               f'WHERE NOT EXISTS (SELECT 1 FROM `part` WHERE `id`={new_part}) AND EXISTS '
               f'(SELECT 1 FROM `part` WHERE `id`=1370 AND SHA2(`DATA`,256)={quote(hashlib.sha256(parts[1370]["data"].encode()).hexdigest())});')
    sql.append(f'UPDATE `mini_pet` m JOIN `part` p ON p.`id`={new_part} AND p.`TYPE`=1 AND p.`DATA`={quote(payload)} '
               f'JOIN `item_template` i ON i.`id`=m.`id_temp` AND i.`TYPE`=21 AND i.`icon_id`=20827 '
               f'SET m.`body`={new_part} WHERE m.`id_temp`=1322 AND m.`head`=1369 AND m.`body`=1370 AND m.`leg`=1371;')
    assets.update(icon_path(f[0], z).as_posix() for f in frames for z in range(1, 5))
    report['pet1322']['new_body'] = new_part

    # Broly's portrait comes from his own model, not the unrelated cyan Broly icon.
    image_id = 32602
    assert all(int(i['icon_id']) != image_id for i in items.values())
    for z in range(1, 5):
        image = Image.open(icon_path(18591, z)).convert('RGBA')
        image = image.crop(image.getbbox())
        image.thumbnail((24*z, 24*z), Image.Resampling.NEAREST)
        save_image(image, icon_path(image_id, z))
    update_item(items[2148], 'icon_id', image_id)
    sql.append(f'UPDATE `head_avatar` SET `avatar_id`={image_id} WHERE `head_id`=1442 AND `avatar_id`=9913;')
    report['broly'] = {'item': 2148, 'image': image_id, 'source_image': 18591}
    # Local image 14069 is a blue arm, not Dragon. Keep the item; unlink only
    # the known bad static follow mapping. No speculative replacement creature.
    sql.append('DELETE FROM `pet_follow` WHERE `id_temp`=2097 AND `icon`=14069 '
               'AND `width`=17 AND `height`=10 AND `frame`=1;')
    report['blocked_follow_pets'] = [2054, 2055, 2056, 2057, 2058, 2059, 2060,
                                     2071, 2072, 2073, 2074, 2097]

    # Correct shared part collisions before the runtime switches to stable part IDs.
    verified_aliases = {740: 37, 741: 38, 774: 8, 784: 18, 791: 25, 800: 40, 801: 41,
                        802: 42, 803: 43, 804: 44, 805: 45, 814: 46, 815: 47, 816: 48,
                        817: 49, 823: 51, 852: 52, 983: 58, 1278: 78, 1279: 79,
                        2110: 98, 2111: 99, 2112: 100, 2113: 101, 2114: 102,
                        2131: 104, 2132: 105, 2133: 106, 2140: 107, 2141: 108, 2143: 109}
    # Their named flag is also wrong (axe/ghost/another sword), so use their own art.
    force_static = {1013, 2106}
    next_flag = 110
    for id, i in sorted(items.items()):
        if int(i['type']) not in (11, 17) or id < 467 or 1993 <= id <= 1998:
            continue  # Quest objects and Namek balls are not back accessories.
        old = int(i['part'])
        candidates = ([flags.get(verified_aliases[id])] if id in verified_aliases else
                      [f for f in flags.values() if f['name'].casefold() == i['name'].casefold()])
        selected = next((f for f in candidates if valid_flag(f)), None)
        if id in force_static:
            selected = None
        if selected:
            new = int(selected['id'])
            mode = 'existing_animation'
            assets.update(icon_path(int(v), z).as_posix() for v in selected['icon_data'].split(',') for z in range(1, 5))
        elif old >= 201 and old in [201, 205, 207]:
            # Genuine native effect accessories need no flag_bag row.
            new = old
            mode = 'native_effect'
        elif has_icon(int(i['icon_id'])) and id != 1298:
            while next_flag in flags:
                next_flag += 1
            assert next_flag < 200, 'Flag byte namespace exhausted'
            new = next_flag
            next_flag += 1
            sql.append(f'INSERT INTO `flag_bag` (`id`,`NAME`,`icon_id`,`icon_data`,`gold`,`gem`) '
                       f'SELECT {new},{quote(i["name"])},{i["icon_id"]},{quote(i["icon_id"])},-1,-1 '
                       f'WHERE NOT EXISTS (SELECT 1 FROM `flag_bag` WHERE `id`={new});')
            assets.update(icon_path(int(i['icon_id']), z).as_posix() for z in range(1, 5))
            mode = 'same_item_static'
        else:
            # Explicitly unlink bad mappings, preventing runtime from rendering another item.
            new = -1
            mode = 'blocked_missing_assets'
            report['blocked_backs'].append(id)
        update_item(i, 'part', new)
        if old != new or mode != 'existing_animation':
            report['backs'].append({'item': id, 'old': old, 'part': new, 'mode': mode})

    # Missing named mount layers: same mount icon as a static front; transparent back.
    known_names = {r['name'] for r in data['img_by_name']}
    for part in [11, 12, 13, 14, 15, 16, 66]:
        i = next(i for i in items.values() if int(i['type']) in [23, 24] and int(i['part']) == part)
        for layer in [0, 1]:
            name = f'mount_{part}_{layer}'
            if name in known_names:
                continue
            for z in range(1, 5):
                source = Image.new('RGBA', (z, z)) if layer == 0 else Image.open(icon_path(int(i['icon_id']), z))
                save_image(source, Path(f'Server/resources/ThanhBN/img_by_name/x{z}/{name}.png'))
            sql.append(f'INSERT INTO `img_by_name` (`name`,`n_frame`) SELECT {quote(name)},1 '
                       f'WHERE NOT EXISTS (SELECT 1 FROM `img_by_name` WHERE `name`={quote(name)});')
        report['mounts'].append({'item': int(i['id']), 'part': part, 'mode': 'existing_front_animation' if part == 66 else 'same_mount_static'})

    # Bounds in these title definitions exceed the actual same-ID atlas. Clip modules
    # to its real rectangle, preserving frame order/positions and the original artwork.
    for effect in [214, 217, 218]:
        for z in range(1, 5):
            folder = Path(f'Server/Eff/effect/x{z}')
            png = Image.open(folder / f'img/ImgEffect_{effect}.png')
            w, h = png.width // z, png.height // z
            path = folder / f'data/DataEffect_{effect}'
            payload = bytearray(path.read_bytes())
            for n in range(payload[0]):
                a = 1 + n*5
                _, x, y, mw, mh = payload[a:a+5]
                assert x < w and y < h
                payload[a+3] = min(mw, w-x)
                payload[a+4] = min(mh, h-y)
            path.write_bytes(payload)
            assets.add(path.as_posix())
    # Title icons are a real module from their effect, replacing unrelated inventory art.
    for i in items.values():
        if int(i['type']) != 39:
            continue
        if int(i['id']) == 1308:
            update_item(i, 'part', -1)  # Check-var title incorrectly points at Halloween.
            report['titles'].append({'item': 1308, 'mode': 'blocked_wrong_effect', 'old': 87})
            continue
        image_id += 1
        assert all(int(i['icon_id']) != image_id for i in items.values())
        effect = int(i['part'])
        for z in range(1, 5):
            folder = Path(f'Server/Eff/effect/x{z}')
            path = folder / f'img/ImgEffect_{effect}.png'
            source_z = z
            if not path.exists():
                source_z = 1
                path = Path(f'Server/Eff/effect/x1/img/ImgEffect_{effect}.png')
            image = Image.open(path).convert('RGBA')
            b = (folder / f'data/DataEffect_{effect}').read_bytes()
            _, x, y, w, h = b[1:6]
            image = image.crop((x*source_z, y*source_z, (x+w)*source_z, (y+h)*source_z))
            if source_z != z:
                image = image.resize((w*z, h*z), Image.Resampling.NEAREST)
            image.thumbnail((28*z, 14*z), Image.Resampling.NEAREST)
            save_image(image, icon_path(image_id, z))
        update_item(i, 'icon_id', image_id)
        report['titles'].append({'item': int(i['id']), 'effect': effect, 'icon': image_id})

    # A complete model is sufficient to derive its missing inventory portrait.
    # Use its own head (or a full pet pose), never a neighboring numeric icon.
    report['icons_from_parts'] = []
    mini = {int(r['id_temp']): r for r in data['mini_pet']}
    for id, i in sorted(items.items()):
        kind = int(i['type'])
        if kind not in [5, 18, 21] or has_icon(int(i['icon_id'])):
            continue
        mapping = (maps if kind == 5 else mini).get(id)
        if not mapping:
            continue
        ids = [int(mapping[k]) for k in ['head', 'body', 'leg']]
        available = [pid for slot, pid in enumerate(ids) if pid >= 0 and pid in parts and int(parts[pid]['type']) == slot]
        if not available or (kind != 5 and len(available) != 3):
            continue
        if any(not has_icon(f[0]) for pid in available for f in json.loads(parts[pid]['data']) if f and f[0] > 0):
            continue
        candidates = [f[0] for pid in ([ids[0]] if kind == 5 and ids[0] in available else available)
                      for f in json.loads(parts[pid]['data']) if f and f[0] > 0]
        def area(pid):
            box = Image.open(icon_path(pid, 4)).convert('RGBA').getbbox()
            return (box[2]-box[0])*(box[3]-box[1]) if box else 0
        # First head/body pose is the model's neutral view. Later rows often
        # contain shared human/flight placeholders (e.g. image 20), not a face.
        source = next((candidate for candidate in candidates if area(candidate) > 0 and candidate not in [16, 20, 34, 2955]), None)
        if source is None:
            continue
        if area(source) == 0:
            continue
        image_id += 1
        assert image_id < 32768 and all(int(row['icon_id']) != image_id for row in items.values())
        for z in range(1, 5):
            image = Image.open(icon_path(source, z)).convert('RGBA')
            image = image.crop(image.getbbox())
            image.thumbnail((24*z, 24*z), Image.Resampling.NEAREST)
            save_image(image, icon_path(image_id, z))
        update_item(i, 'icon_id', image_id)
        report['icons_from_parts'].append({'item': id, 'icon': image_id, 'source_image': source, 'parts': ids})
        assets.update(icon_path(f[0], z).as_posix() for pid in available
                      for f in json.loads(parts[pid]['data']) if f and f[0] > 0 for z in range(1, 5))
        if kind == 5 and ids[0] >= 0:
            avatar = next((r for r in data['head_avatar'] if int(r['head_id']) == ids[0]), None)
            if avatar:
                sql.append(f'UPDATE `head_avatar` SET `avatar_id`={image_id} WHERE `head_id`={ids[0]} AND `avatar_id`={avatar["avatar_id"]};')

    for effect in [84, 85, 86, 87, 88, 89, 201, 205, 207, 214, 215, 217, 218]:
        for z in range(1, 5):
            for file in [f'data/DataEffect_{effect}', f'img/ImgEffect_{effect}.png']:
                path = Path(f'Server/Eff/effect/x{z}') / file
                if path.exists():
                    assets.add(path.as_posix())
    report['auras'] = {'transparent_missing_layers': ['aura_1_0', 'aura_10_1'], 'blocked_missing_sets': [11, 12]}
    for name in ['aura_1_0', 'aura_10_1']:
        frames = int(next(r['n_frame'] for r in data['img_by_name'] if r['name'] == name))
        for z in range(1, 5):
            save_image(Image.new('RGBA', (z, z*frames)), Path(f'Server/resources/ThanhBN/img_by_name/x{z}/{name}.png'))
    sql.append('UPDATE `admin_editor_state` SET `data_version`=31,`item_version`=29 '
               'WHERE `id`=1 AND `data_version`=30 AND `item_version`=28;')
    Path('db/migrations/V30__repair_remaining_visual_equipment.sql').write_bytes(('\n'.join(sql)+'\n').encode('utf-8'))
    report['assets'] = sorted(assets)
    Path('tools/part-editor/remaining-visual-repairs.json').write_bytes((json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in report.items() if k != 'assets'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
