-- Santa's main shop: reserve a tab for the special mystery box gifts.
-- The <> separator is rendered as a line break by ShopDAO.
INSERT INTO tab_shop (shop_id, NAME)
SELECT shop.id, 'Hộp mù<>đặc biệt'
FROM shop
WHERE shop.npc_id = 39
  AND shop.shop_order = 0
  AND NOT EXISTS (
      SELECT 1
      FROM tab_shop tab
      WHERE tab.shop_id = shop.id
        AND REPLACE(tab.NAME, '<>', ' ') = 'Hộp mù đặc biệt'
  );
