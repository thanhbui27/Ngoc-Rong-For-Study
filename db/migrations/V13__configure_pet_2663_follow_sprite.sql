-- The historical dump maps pet 2663 to icon 57, a 1x1 image, with 69 frames.
-- Use the available 2663 icon as a single static frame until a sprite sheet is supplied.
INSERT INTO pet_follow (id_temp, icon, width, height, frame)
SELECT 2663, 2663, 31, 19, 1
WHERE NOT EXISTS (SELECT 1 FROM pet_follow WHERE id_temp = 2663);

UPDATE pet_follow
SET icon = 2663, width = 31, height = 19, frame = 1
WHERE id_temp = 2663 AND icon = 57 AND width = 106 AND height = 67 AND frame = 69;
