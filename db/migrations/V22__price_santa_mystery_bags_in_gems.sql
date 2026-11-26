-- Green gems: normal bags 50, VIP bags 100, special bag 500.
-- Keep earlier migrations unchanged for databases that already applied them.
UPDATE item_shop sale
JOIN tab_shop tab ON tab.id = sale.tab_id
JOIN shop ON shop.id = tab.shop_id
JOIN item_template gift ON gift.id = sale.temp_id
SET sale.gold = 0,
    sale.gem = CASE gift.id
        WHEN 3000 THEN 50
        WHEN 3001 THEN 100
        WHEN 3002 THEN 50
        WHEN 3003 THEN 100
        WHEN 3004 THEN 500
    END,
    sale.is_sell = 1
WHERE shop.npc_id = 39
  AND shop.shop_order = 0
  AND REPLACE(tab.NAME, '<>', ' ') = 'Hộp mù đặc biệt'
  AND ((gift.id = 3000 AND gift.icon_id = 14518)
    OR (gift.id = 3001 AND gift.icon_id = 14519)
    OR (gift.id = 3002 AND gift.icon_id = 14520)
    OR (gift.id = 3003 AND gift.icon_id = 14521)
    OR (gift.id = 3004 AND gift.icon_id = 14522));

UPDATE item_template
SET description = 'Chưa thể mở, phần thưởng đang được cập nhật'
WHERE (id = 3000 AND icon_id = 14518)
   OR (id = 3001 AND icon_id = 14519)
   OR (id = 3002 AND icon_id = 14520)
   OR (id = 3003 AND icon_id = 14521)
   OR (id = 3004 AND icon_id = 14522);

UPDATE item_template
SET NAME = 'Túi Mù Đặc Biệt'
WHERE id = 3004 AND icon_id = 14522;
