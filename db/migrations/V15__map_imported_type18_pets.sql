-- Reuse verified mini_pet part mappings when a server-14 type-18 pet was
-- imported under a new local item ID. Do not guess parts for unmapped pets.
-- Drop server-14 pet copies when the local catalog already has the same
-- named MiniPet, or an earlier import has the same name and icon.
CREATE TEMPORARY TABLE duplicate_imported_pet (id INT PRIMARY KEY);
INSERT INTO duplicate_imported_pet (id)
SELECT DISTINCT imported.id
FROM admin_catalog_item_source source
JOIN item_template imported ON imported.id = source.item_id AND imported.TYPE = 18
JOIN item_template original ON original.id < imported.id
  AND original.TYPE IN (21, 27) AND original.gender = imported.gender
  AND BINARY original.NAME = BINARY imported.NAME
JOIN mini_pet original_parts ON original_parts.id_temp = original.id
WHERE source.source_server = 'dragon14.teamobi.com:18001';

INSERT IGNORE INTO duplicate_imported_pet (id)
SELECT imported.id
FROM admin_catalog_item_source source
JOIN item_template imported ON imported.id = source.item_id AND imported.TYPE = 18
JOIN item_template earlier ON earlier.id < imported.id AND earlier.TYPE = 18
  AND earlier.gender = imported.gender AND earlier.icon_id = imported.icon_id
  AND BINARY earlier.NAME = BINARY imported.NAME
WHERE source.source_server = 'dragon14.teamobi.com:18001';

DELETE mapping FROM mini_pet mapping JOIN duplicate_imported_pet duplicate ON duplicate.id = mapping.id_temp;
DELETE sprite FROM pet_follow sprite JOIN duplicate_imported_pet duplicate ON duplicate.id = sprite.id_temp;
DELETE source FROM admin_catalog_item_source source JOIN duplicate_imported_pet duplicate ON duplicate.id = source.item_id;
DELETE item FROM item_template item JOIN duplicate_imported_pet duplicate ON duplicate.id = item.id;
DROP TEMPORARY TABLE duplicate_imported_pet;

-- Two legacy pets were stored as generic type 27 despite having full parts.
UPDATE item_template item
JOIN reference_item_template reference_item
  ON reference_item.source_server = 'dragon14.teamobi.com:18001'
 AND reference_item.id = item.id
 AND reference_item.item_type = 18
 AND BINARY reference_item.name = BINARY item.NAME
JOIN mini_pet mapped
  ON mapped.id_temp = item.id
 AND mapped.head >= 0
 AND mapped.body >= 0
 AND mapped.leg >= 0
SET item.TYPE = 21
WHERE item.TYPE = 27;

INSERT INTO mini_pet (id_temp, head, body, leg)
SELECT source.item_id, mapped.head, mapped.body, mapped.leg
FROM admin_catalog_item_source source
JOIN reference_item_template reference_item
  ON reference_item.source_server = source.source_server
 AND reference_item.id = source.source_item_id
 AND reference_item.item_type = 18
JOIN item_template item
  ON item.id = source.item_id
 AND item.TYPE = 18
JOIN mini_pet mapped
  ON mapped.id_temp = source.source_item_id
 AND mapped.head >= 0
 AND mapped.body >= 0
 AND mapped.leg >= 0
WHERE source.source_server = 'dragon14.teamobi.com:18001'
  AND NOT EXISTS (
    SELECT 1 FROM mini_pet existing WHERE existing.id_temp = source.item_id
  );

-- Keep the source type in reference_item_template, but use the local
-- MiniPet type for all playable items with part-based sprites.
UPDATE item_template SET TYPE = 21 WHERE TYPE = 18;

-- MiniPet items never use a pet_follow sprite. V14 inserted static follow
-- rows for imported type-18 items; remove those obsolete rows as well as any
-- legacy type-21 follow rows.
DELETE follow_sprite
FROM pet_follow follow_sprite
JOIN item_template item ON item.id = follow_sprite.id_temp
WHERE item.TYPE = 21;
