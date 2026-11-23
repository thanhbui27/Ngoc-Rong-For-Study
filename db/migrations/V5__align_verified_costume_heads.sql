-- Align four costume heads only where the existing BE item identity and old
-- mapping match the verified server 14 template. The target head parts are
-- already present in this BE's part table and match the server part frames.
-- Other costume and pet mappings are intentionally untouched: the client item
-- template does not contain their full head/body/leg/bag mapping.

UPDATE `cai_trang` AS ct
JOIN `item_template` AS it ON it.`id` = ct.`id_temp`
SET ct.`head` = 0
WHERE ct.`id_temp` = 210 AND ct.`head` = 17
  AND it.`TYPE` = 5 AND it.`gender` = 0 AND it.`NAME` = 'Avatar'
  AND it.`icon_id` = 17 AND it.`part` = 0
  AND EXISTS (SELECT 1 FROM `part` AS p WHERE p.`id` = 0 AND p.`TYPE` = 0);

UPDATE `cai_trang` AS ct
JOIN `item_template` AS it ON it.`id` = ct.`id_temp`
SET ct.`head` = 277
WHERE ct.`id_temp` = 386 AND ct.`head` = 227
  AND it.`TYPE` = 5 AND it.`gender` = 0 AND it.`NAME` = 'Nón Noel Xám'
  AND it.`icon_id` = 2782 AND it.`part` = 277
  AND EXISTS (SELECT 1 FROM `part` AS p WHERE p.`id` = 277 AND p.`TYPE` = 0);

UPDATE `cai_trang` AS ct
JOIN `item_template` AS it ON it.`id` = ct.`id_temp`
SET ct.`head` = 856
WHERE ct.`id_temp` = 872 AND ct.`head` = 857
  AND it.`TYPE` = 5 AND it.`gender` = 0 AND it.`NAME` = 'Avatar Gohan 1'
  AND it.`icon_id` = 7855 AND it.`part` = 856
  AND EXISTS (SELECT 1 FROM `part` AS p WHERE p.`id` = 856 AND p.`TYPE` = 0);

UPDATE `cai_trang` AS ct
JOIN `item_template` AS it ON it.`id` = ct.`id_temp`
SET ct.`head` = 857
WHERE ct.`id_temp` = 873 AND ct.`head` = 856
  AND it.`TYPE` = 5 AND it.`gender` = 0 AND it.`NAME` = 'Avatar Gohan 2'
  AND it.`icon_id` = 7858 AND it.`part` = 857
  AND EXISTS (SELECT 1 FROM `part` AS p WHERE p.`id` = 857 AND p.`TYPE` = 0);
