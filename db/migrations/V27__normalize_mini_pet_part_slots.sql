-- Preserve each pet's three existing parts, assigning each to its declared role.
-- Only repair complete permutations (one head, one body, one leg); never guess a missing part.
UPDATE `mini_pet` m
JOIN `item_template` i ON i.`id`=m.`id_temp` AND i.`TYPE` IN (18,21)
JOIN `part` h ON h.`id`=m.`head`
JOIN `part` b ON b.`id`=m.`body`
JOIN `part` l ON l.`id`=m.`leg`
SET m.`head`=CASE WHEN h.`TYPE`=0 THEN h.`id` WHEN b.`TYPE`=0 THEN b.`id` ELSE l.`id` END,
    m.`body`=CASE WHEN h.`TYPE`=1 THEN h.`id` WHEN b.`TYPE`=1 THEN b.`id` ELSE l.`id` END,
    m.`leg`=CASE WHEN h.`TYPE`=2 THEN h.`id` WHEN b.`TYPE`=2 THEN b.`id` ELSE l.`id` END
WHERE h.`TYPE` IN (0,1,2) AND b.`TYPE` IN (0,1,2) AND l.`TYPE` IN (0,1,2)
 AND h.`TYPE`<>b.`TYPE` AND h.`TYPE`<>l.`TYPE` AND b.`TYPE`<>l.`TYPE`
 AND (h.`TYPE`<>0 OR b.`TYPE`<>1 OR l.`TYPE`<>2);
