-- Add Nho xanh (item 212) to each planet's special shop tab.
-- These are the same NPC shops used in the planet villages and the supermarket.
-- Safe to run on an existing database; each tab gets the item only once.
INSERT INTO `item_shop`
    (`tab_id`, `temp_id`, `gold`, `gem`, `is_new`, `is_sell`, `item_exchange`, `quantity_exchange`)
SELECT 3, 212, 1000, 0, 0, 1, -1, 0
WHERE NOT EXISTS (
    SELECT 1 FROM `item_shop` WHERE `tab_id` = 3 AND `temp_id` = 212
);

INSERT INTO `item_shop`
    (`tab_id`, `temp_id`, `gold`, `gem`, `is_new`, `is_sell`, `item_exchange`, `quantity_exchange`)
SELECT 6, 212, 1000, 0, 0, 1, -1, 0
WHERE NOT EXISTS (
    SELECT 1 FROM `item_shop` WHERE `tab_id` = 6 AND `temp_id` = 212
);

INSERT INTO `item_shop`
    (`tab_id`, `temp_id`, `gold`, `gem`, `is_new`, `is_sell`, `item_exchange`, `quantity_exchange`)
SELECT 9, 212, 1000, 0, 0, 1, -1, 0
WHERE NOT EXISTS (
    SELECT 1 FROM `item_shop` WHERE `tab_id` = 9 AND `temp_id` = 212
);
