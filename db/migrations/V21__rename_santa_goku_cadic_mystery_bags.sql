-- Keep V20 unchanged for databases that already recorded its checksum.
-- Match both the item ID and icon so unrelated templates are untouched.
UPDATE item_template
SET NAME = CASE id
    WHEN 3000 THEN 'Túi Mù Goku'
    WHEN 3001 THEN 'Túi Mù Goku VIP'
    WHEN 3002 THEN 'Túi Mù Cadic'
    WHEN 3003 THEN 'Túi Mù Cadic VIP'
END
WHERE (id = 3000 AND icon_id = 14518)
   OR (id = 3001 AND icon_id = 14519)
   OR (id = 3002 AND icon_id = 14520)
   OR (id = 3003 AND icon_id = 14521);
