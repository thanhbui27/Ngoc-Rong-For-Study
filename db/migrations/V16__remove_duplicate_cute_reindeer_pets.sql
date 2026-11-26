-- Keep the configured MiniPet 2152. The older 1211 and imported 2616
-- have the same name and no part mapping.
CREATE TEMPORARY TABLE duplicate_cute_reindeer (id INT PRIMARY KEY);

INSERT INTO duplicate_cute_reindeer (id)
SELECT duplicate.id
FROM item_template duplicate
JOIN item_template canonical ON canonical.id = 2152 AND canonical.TYPE = 21
JOIN mini_pet mapping ON mapping.id_temp = canonical.id
  AND mapping.head >= 0 AND mapping.body >= 0 AND mapping.leg >= 0
WHERE duplicate.id IN (1211, 2616)
  AND duplicate.TYPE = 21
  AND duplicate.NAME COLLATE utf8mb4_general_ci = canonical.NAME COLLATE utf8mb4_general_ci;

DELETE source FROM admin_catalog_item_source source
JOIN duplicate_cute_reindeer duplicate ON duplicate.id = source.item_id;
DELETE sprite FROM pet_follow sprite
JOIN duplicate_cute_reindeer duplicate ON duplicate.id = sprite.id_temp;
DELETE mapping FROM mini_pet mapping
JOIN duplicate_cute_reindeer duplicate ON duplicate.id = mapping.id_temp;
DELETE item FROM item_template item
JOIN duplicate_cute_reindeer duplicate ON duplicate.id = item.id;

DROP TEMPORARY TABLE duplicate_cute_reindeer;
