-- Pet 2663 already has a pet_follow mapping in the seed, but no item template.
-- Keep existing names and icons on databases where the item was added later.
INSERT INTO item_template
  (id, TYPE, gender, NAME, description, icon_id, part, is_up_to_up, power_require)
SELECT 2663, 72, 3, 'Pet 2663', 'Pet đi theo', 2663, -1, 0, 0
WHERE NOT EXISTS (SELECT 1 FROM item_template WHERE id = 2663);

UPDATE item_template
SET TYPE = 72, gender = 3, power_require = 0
WHERE id = 2663;
