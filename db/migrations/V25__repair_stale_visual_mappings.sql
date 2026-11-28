-- Repair visual configuration verified against this checkout's resource files.
-- Preserve current/custom mappings unless they still match the obsolete seed row.
-- V24 may have replaced some of these IDs with source costumes; TYPE=5 protects them.
DELETE FROM `cai_trang`
WHERE EXISTS (SELECT 1 FROM `item_template` t WHERE t.`id` = `cai_trang`.`id_temp` AND t.`TYPE` <> 5) AND (
  (`id_temp` = 1287 AND `head` = 1273 AND `body` = 1274 AND `leg` = 1275) OR
  (`id_temp` = 1288 AND `head` = 1276 AND `body` = 1277 AND `leg` = 1278) OR
  (`id_temp` = 1318 AND `head` = 1270 AND `body` = 1271 AND `leg` = 1272) OR
  (`id_temp` = 1350 AND `head` = 1243 AND `body` = 1244 AND `leg` = 1245) OR
  (`id_temp` = 1359 AND `head` = 1264 AND `body` = 1265 AND `leg` = 1266) OR
  (`id_temp` = 1360 AND `head` = 1267 AND `body` = 1268 AND `leg` = 1269)
);

-- Remove obsolete pet records only for identities actually adopted by V24.
DELETE FROM `pet_follow`
WHERE EXISTS (
  SELECT 1 FROM `item_template` t
  JOIN `reference_item_template` s
    ON s.`source_server` = 'dragon14.teamobi.com:18001' AND s.`id` = t.`id`
  WHERE t.`id` = `pet_follow`.`id_temp` AND t.`TYPE` = 5 AND s.`item_type` = 5
    AND t.`NAME` = s.`name` AND t.`icon_id` = s.`icon_id`
);

DELETE FROM `mini_pet`
WHERE EXISTS (
  SELECT 1 FROM `item_template` t
  JOIN `reference_item_template` s
    ON s.`source_server` = 'dragon14.teamobi.com:18001' AND s.`id` = t.`id`
  WHERE t.`id` = `mini_pet`.`id_temp` AND t.`TYPE` = 5 AND s.`item_type` = 5
    AND t.`NAME` = s.`name` AND t.`icon_id` = s.`icon_id`
);

-- Dragon #2097 has a real 17x10 static icon (x1), not a 75x75x8 sprite sheet.
-- This persists the existing PetFollowManager static fallback honestly.
UPDATE `pet_follow`
SET `width` = 17, `height` = 10, `frame` = 1
WHERE `id_temp` = 2097 AND `icon` = 14069 AND `width` = 75 AND `height` = 75 AND `frame` = 8
  AND EXISTS (SELECT 1 FROM `item_template` t WHERE t.`id` = `pet_follow`.`id_temp`
              AND t.`TYPE` = 72 AND t.`icon_id` = 14069);
