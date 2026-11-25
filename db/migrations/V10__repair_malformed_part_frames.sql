-- Part packets do not include per-part frame counts. The client derives each count
-- from TYPE, so these placeholder rows must contain the complete fixed-size arrays.
UPDATE `part`
SET `DATA` = '[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]'
WHERE `id` = 1904 AND `TYPE` = 1 AND JSON_LENGTH(`DATA`) <> 17;

UPDATE `part`
SET `DATA` = '[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]'
WHERE `id` = 1905 AND `TYPE` = 2 AND JSON_LENGTH(`DATA`) <> 14;

-- Force existing clients to replace their already-corrupt cached NR_part file.
UPDATE `admin_editor_state`
SET `data_version` = CASE WHEN `data_version` >= 120 THEN 1 ELSE `data_version` + 1 END
WHERE `id` = 1;
