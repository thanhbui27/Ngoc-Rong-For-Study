-- Match the first 10 base-damage caps to the NRO milestone reference table.
-- Preserve the server's custom power thresholds and its existing top two caps.
UPDATE `power_limit`
SET `damage` = CASE `id`
    WHEN 1 THEN 11000
    WHEN 2 THEN 12000
    WHEN 3 THEN 15000
    WHEN 4 THEN 18000
    WHEN 5 THEN 20000
    WHEN 6 THEN 22000
    WHEN 7 THEN 24000
    WHEN 8 THEN 24500
    WHEN 9 THEN 25000
    WHEN 10 THEN 26000
    ELSE `damage`
END
WHERE `id` BETWEEN 1 AND 10;
