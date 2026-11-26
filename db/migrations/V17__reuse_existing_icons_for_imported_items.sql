-- V9 gave server-14 catalog items new icon IDs 32212-32581 to preserve
-- different images at the same source IDs. Reuse the existing local icons
-- instead of shipping a second copy of those 370 images at four zoom levels.
UPDATE item_template item
JOIN admin_catalog_item_source imported ON imported.item_id = item.id
JOIN admin_catalog_icon_alias icon ON icon.item_icon_id = item.icon_id
SET item.icon_id = icon.source_icon_id
WHERE imported.source_server = 'dragon14.teamobi.com:18001'
  AND icon.item_icon_id BETWEEN 32212 AND 32581;

DELETE FROM admin_catalog_icon_alias
WHERE item_icon_id BETWEEN 32212 AND 32581;
