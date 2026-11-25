-- Part Studio previously saved cai_trang without registering its head avatar.
-- Pan VIP's item icon is the portrait sent as avatar for head part 2097.
INSERT INTO head_avatar (head_id, avatar_id)
SELECT c.head, t.icon_id
FROM cai_trang c
JOIN item_template t ON t.id = c.id_temp
WHERE t.id = 2682 AND t.TYPE = 5 AND c.head = 2097 AND t.icon_id = 16131
  AND NOT EXISTS (SELECT 1 FROM head_avatar a WHERE a.head_id = c.head);
