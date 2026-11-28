-- Repair five legacy mini-pet mappings whose IDs collided with unrelated local parts.
-- Require exact source identity and the known old mapping; preserve all other custom pets.
CREATE TEMPORARY TABLE `visual_mini_source` (
 `source_item_id` INT PRIMARY KEY, `head` INT NOT NULL, `body` INT NOT NULL, `leg` INT NOT NULL
);
INSERT INTO `visual_mini_source` VALUES
(1224,1227,1228,1229),(1225,1233,1234,1235),(1226,1230,1231,1232),(1243,1245,1246,1247),(1244,1248,1249,1250);
CREATE TEMPORARY TABLE `visual_mini_target` (`item_id` INT PRIMARY KEY, `source_item_id` INT NOT NULL);
INSERT IGNORE INTO `visual_mini_target`
SELECT t.`id`, m.`source_item_id`
FROM `admin_catalog_item_source` imported
JOIN `visual_mini_source` m ON m.`source_item_id`=imported.`source_item_id`
JOIN `reference_item_template` s ON s.`source_server`=imported.`source_server` AND s.`id`=m.`source_item_id`
JOIN `item_template` t ON t.`id`=imported.`item_id`
WHERE imported.`source_server`='dragon14.teamobi.com:18001'
 AND s.`item_type` IN (18,21) AND t.`TYPE` IN (18,21)
 AND t.`NAME`=s.`name` AND t.`gender`=s.`gender` AND t.`icon_id`=s.`icon_id`
 AND EXISTS (SELECT 1 FROM `mini_pet` old WHERE old.`id_temp`=t.`id` AND ((t.`id`=1224 AND old.`head`=1228 AND old.`body`=1229 AND old.`leg`=1227) OR (t.`id`=1225 AND old.`head`=1234 AND old.`body`=1235 AND old.`leg`=1233) OR (t.`id`=1226 AND old.`head`=1231 AND old.`body`=1232 AND old.`leg`=1230) OR (t.`id`=1243 AND old.`head`=1246 AND old.`body`=1247 AND old.`leg`=1245) OR (t.`id`=1244 AND old.`head`=1249 AND old.`body`=1250 AND old.`leg`=1248)));
INSERT IGNORE INTO `visual_mini_target`
SELECT t.`id`, m.`source_item_id`
FROM `visual_mini_source` m
JOIN `reference_item_template` s ON s.`id`=m.`source_item_id` AND s.`source_server`='dragon14.teamobi.com:18001'
JOIN `item_template` t ON t.`id`=m.`source_item_id`
WHERE s.`item_type` IN (18,21) AND t.`TYPE` IN (18,21)
 AND t.`NAME`=s.`name` AND t.`gender`=s.`gender` AND t.`icon_id`=s.`icon_id`
 AND EXISTS (SELECT 1 FROM `mini_pet` old WHERE old.`id_temp`=t.`id` AND ((t.`id`=1224 AND old.`head`=1228 AND old.`body`=1229 AND old.`leg`=1227) OR (t.`id`=1225 AND old.`head`=1234 AND old.`body`=1235 AND old.`leg`=1233) OR (t.`id`=1226 AND old.`head`=1231 AND old.`body`=1232 AND old.`leg`=1230) OR (t.`id`=1243 AND old.`head`=1246 AND old.`body`=1247 AND old.`leg`=1245) OR (t.`id`=1244 AND old.`head`=1249 AND old.`body`=1250 AND old.`leg`=1248)));
CREATE TEMPORARY TABLE `visual_mini_needed` AS
 SELECT m.`head` AS `source_part_id` FROM `visual_mini_source` m JOIN `visual_mini_target` t ON t.`source_item_id`=m.`source_item_id`
 UNION SELECT m.`body` FROM `visual_mini_source` m JOIN `visual_mini_target` t ON t.`source_item_id`=m.`source_item_id`
 UNION SELECT m.`leg` FROM `visual_mini_source` m JOIN `visual_mini_target` t ON t.`source_item_id`=m.`source_item_id`;
CREATE TEMPORARY TABLE `visual_mini_resolved` (`source_part_id` INT PRIMARY KEY, `part_id` INT NOT NULL);
INSERT IGNORE INTO `visual_mini_resolved`
SELECT n.`source_part_id`, a.`part_id`
FROM `visual_mini_needed` n
JOIN `admin_part_alias` a ON a.`source_server`='dragon14.teamobi.com:18001' AND a.`source_part_id`=n.`source_part_id`
JOIN `reference_part` s ON s.`source_server`=a.`source_server` AND s.`id`=n.`source_part_id`
JOIN `part` p ON p.`id`=a.`part_id` AND p.`TYPE`=s.`part_type` AND BINARY p.`DATA`=BINARY s.`data`;
INSERT IGNORE INTO `visual_mini_resolved`
SELECT n.`source_part_id`, p.`id` FROM `visual_mini_needed` n
JOIN `reference_part` s ON s.`source_server`='dragon14.teamobi.com:18001' AND s.`id`=n.`source_part_id`
JOIN `part` p ON p.`id`=n.`source_part_id` AND p.`TYPE`=s.`part_type` AND BINARY p.`DATA`=BINARY s.`data`;
INSERT IGNORE INTO `visual_mini_resolved`
SELECT n.`source_part_id`, MIN(p.`id`) FROM `visual_mini_needed` n
JOIN `reference_part` s ON s.`source_server`='dragon14.teamobi.com:18001' AND s.`id`=n.`source_part_id`
JOIN `part` p ON p.`TYPE`=s.`part_type` AND BINARY p.`DATA`=BINARY s.`data`
GROUP BY n.`source_part_id`;
SET @visual_mini_start=(SELECT COALESCE(MAX(`id`),-1)+1 FROM `part`);
CREATE TEMPORARY TABLE `visual_mini_new` AS
SELECT n.`source_part_id`, @visual_mini_start+ROW_NUMBER() OVER (ORDER BY n.`source_part_id`)-1 AS `part_id`
FROM `visual_mini_needed` n LEFT JOIN `visual_mini_resolved` p ON p.`source_part_id`=n.`source_part_id`
WHERE p.`source_part_id` IS NULL;
CREATE TEMPORARY TABLE `visual_mini_integrity` (`id` INT PRIMARY KEY);
INSERT INTO `visual_mini_integrity` VALUES (1);
INSERT INTO `visual_mini_integrity` SELECT 1 WHERE EXISTS (SELECT 1 FROM `visual_mini_new` WHERE `part_id`>32767)
 OR EXISTS (SELECT 1 FROM `visual_mini_needed` n LEFT JOIN `reference_part` s
 ON s.`source_server`='dragon14.teamobi.com:18001' AND s.`id`=n.`source_part_id` WHERE s.`id` IS NULL);
INSERT INTO `part` (`id`,`TYPE`,`DATA`)
SELECT fresh.`part_id`,s.`part_type`,s.`data` FROM `visual_mini_new` fresh
JOIN `reference_part` s ON s.`source_server`='dragon14.teamobi.com:18001' AND s.`id`=fresh.`source_part_id`;
INSERT INTO `admin_part_alias` (`source_server`,`source_part_id`,`part_id`)
SELECT 'dragon14.teamobi.com:18001',`source_part_id`,`part_id` FROM `visual_mini_new` WHERE 1=1
ON DUPLICATE KEY UPDATE `part_id`=VALUES(`part_id`);
INSERT INTO `visual_mini_resolved` SELECT `source_part_id`,`part_id` FROM `visual_mini_new`;
UPDATE `mini_pet` old JOIN `visual_mini_target` t ON t.`item_id`=old.`id_temp`
JOIN `visual_mini_source` m ON m.`source_item_id`=t.`source_item_id`
JOIN `visual_mini_resolved` h ON h.`source_part_id`=m.`head`
JOIN `visual_mini_resolved` b ON b.`source_part_id`=m.`body`
JOIN `visual_mini_resolved` l ON l.`source_part_id`=m.`leg`
SET old.`head`=h.`part_id`,old.`body`=b.`part_id`,old.`leg`=l.`part_id`;
UPDATE `admin_editor_state` SET `data_version`=CASE WHEN `data_version`>=120 THEN 1 ELSE `data_version`+1 END
WHERE `id`=1 AND EXISTS (SELECT 1 FROM `visual_mini_target`);
DROP TEMPORARY TABLE `visual_mini_integrity`;
DROP TEMPORARY TABLE `visual_mini_new`;
DROP TEMPORARY TABLE `visual_mini_resolved`;
DROP TEMPORARY TABLE `visual_mini_needed`;
DROP TEMPORARY TABLE `visual_mini_target`;
DROP TEMPORARY TABLE `visual_mini_source`;
