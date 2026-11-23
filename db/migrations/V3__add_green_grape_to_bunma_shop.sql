-- Add Nho xanh (item 212) to Bunma's special shop tab for existing databases.
-- The clean seed already contains this row; this migration fills it in on older DBs.
INSERT INTO `item_shop`
    (`id`, `tab_id`, `temp_id`, `gold`, `gem`, `is_new`, `is_sell`, `item_exchange`, `quantity_exchange`)
SELECT (SELECT COALESCE(MAX(`id`), 0) + 1 FROM `item_shop`), 3, 212, 1000, 0, 0, 1, -1, 0
WHERE NOT EXISTS (
    SELECT 1 FROM `item_shop` WHERE `tab_id` = 3 AND `temp_id` = 212
);
