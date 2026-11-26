-- Item IDs are client protocol indexes. Add these after the server-14 import
-- so its existing dynamic item IDs do not shift.
INSERT INTO item_template
    (id, TYPE, gender, NAME, description, icon_id, part, is_up_to_up, power_require)
VALUES
    (3000, 27, 3, 'Hộp Mù Hoàng Kim', 'Trưng bày, chưa mở bán', 14518, -1, 0, 0),
    (3001, 27, 3, 'Hộp Mù Hoàng Kim VIP', 'Trưng bày, chưa mở bán', 14519, -1, 0, 0),
    (3002, 27, 3, 'Hộp Mù Băng Lam', 'Trưng bày, chưa mở bán', 14520, -1, 0, 0),
    (3003, 27, 3, 'Hộp Mù Băng Lam VIP', 'Trưng bày, chưa mở bán', 14521, -1, 0, 0),
    (3004, 27, 3, 'Hộp Mù Hắc Kim', 'Trưng bày, chưa mở bán', 14522, -1, 0, 0);

-- -1/-1 hides purchase actions in the client. The server also rejects direct
-- purchase packets until prices and rewards have been defined.
INSERT INTO item_shop
    (tab_id, temp_id, gold, gem, is_new, is_sell, item_exchange, quantity_exchange)
SELECT tab.id, item.id, -1, -1, 1, 1, -1, 0
FROM shop
JOIN tab_shop tab ON tab.shop_id = shop.id
JOIN item_template item ON item.id BETWEEN 3000 AND 3004
WHERE shop.npc_id = 39
  AND shop.shop_order = 0
  AND REPLACE(tab.NAME, '<>', ' ') = 'Hộp mù đặc biệt'
ORDER BY item.id;
