-- Fill verified source mini pets that currently have no mapping.
-- Keep every existing mini_pet mapping, including adapted/custom frame layouts.
CREATE TEMPORARY TABLE `visual_mini_source` (
 `source_item_id` INT PRIMARY KEY, `head` INT NOT NULL, `body` INT NOT NULL, `leg` INT NOT NULL
);
INSERT INTO `visual_mini_source` VALUES
(892,882,883,884),
(893,885,886,887),
(908,891,892,893),
(909,897,898,899),
(910,894,895,896),
(916,931,932,933),
(917,928,929,930),
(918,925,926,927),
(919,934,935,936),
(936,718,719,720),
(942,966,967,968),
(943,969,970,971),
(944,972,973,974),
(967,1050,1051,1052),
(1008,1074,1075,1076),
(1039,1089,1090,1091),
(1040,1092,1093,1094),
(1046,95,96,97),
(1107,1155,1156,1157),
(1114,1158,1159,1160),
(1188,1183,1184,1185),
(1202,1201,1202,1203),
(1203,1201,1202,1203),
(1207,1077,1078,1079),
(1224,1227,1228,1229),
(1225,1233,1234,1235),
(1226,1230,1231,1232),
(1243,1245,1246,1247),
(1244,1248,1249,1250),
(1256,1267,1268,1269),
(1318,1299,1300,1301),
(1347,1302,1303,1304),
(1414,1341,1342,1343),
(1435,1347,1348,1349),
(1452,1365,1366,1367),
(1458,1368,1369,1370),
(1482,1398,1399,1400),
(1497,1401,1402,1403),
(1550,1428,1429,1430),
(1551,1425,1426,1427),
(1564,1437,1438,1439),
(1568,1443,1444,1445),
(1573,1446,1447,1448),
(1596,1470,1471,1472),
(1597,1473,1474,1475),
(1611,1493,1494,1495),
(1620,1496,1497,1498),
(1621,1496,1497,1498),
(1622,1496,1497,1498),
(1629,1505,1506,1507),
(1630,1508,1509,1510),
(1631,1515,1516,1517),
(1633,1523,1524,1525),
(1654,1528,1529,1530),
(1668,1550,1551,1552),
(1682,1558,1559,1560),
(1683,1561,1562,1563),
(1686,1572,1573,1574),
(1712,1608,1609,1610),
(1714,1600,1601,1602),
(1727,1616,1617,1618),
(1729,1621,1622,1623),
(1748,1650,1651,1652),
(1750,1464,1465,1466),
(1774,1665,1666,1667),
(1786,1689,1690,1691),
(1791,1695,1696,1697),
(1792,1698,1699,1700),
(1793,1701,1702,1703),
(1794,1704,1705,1706),
(1801,1713,1714,1715),
(1802,1716,1717,1718),
(1813,1751,1752,1753),
(1814,1748,1749,1750),
(1815,1745,1746,1747),
(1816,1742,1743,1744),
(1817,1739,1740,1741),
(1818,1736,1737,1738),
(1819,1733,1734,1735),
(1830,1767,1768,1769),
(1845,1784,1785,1786),
(1846,1787,1788,1789),
(1870,1820,1821,1822),
(1871,1823,1824,1825),
(1872,1826,1827,1828),
(1873,1829,1830,1831),
(1874,1832,1833,1834),
(1881,1841,1842,1843),
(1914,1876,1877,1878),
(1929,1888,1889,1890),
(1935,1900,1901,1902),
(1945,1909,1910,1911),
(1953,1921,1922,1923),
(1956,1930,1931,1932),
(1962,1936,1937,1938),
(1964,1939,1940,1941),
(1973,1948,1949,1950),
(1974,1951,1952,1953),
(1975,1954,1955,1956),
(1980,1962,1963,1964),
(2014,1983,1984,1985),
(2015,1980,1981,1982),
(2016,1986,1987,1988),
(2019,1989,1990,1991),
(2025,1997,1998,1999),
(2036,234,235,236),
(2037,264,265,266),
(2038,2009,2010,2011),
(2059,1077,1078,1079),
(2072,2050,2051,2052),
(2077,2056,2057,2058),
(2094,2076,2077,2078);
CREATE TEMPORARY TABLE `visual_mini_target` (`item_id` INT PRIMARY KEY, `source_item_id` INT NOT NULL);
INSERT IGNORE INTO `visual_mini_target`
SELECT t.`id`, m.`source_item_id`
FROM `admin_catalog_item_source` imported
JOIN `visual_mini_source` m ON m.`source_item_id`=imported.`source_item_id`
JOIN `reference_item_template` s ON s.`source_server`=imported.`source_server` AND s.`id`=m.`source_item_id`
JOIN `item_template` t ON t.`id`=imported.`item_id`
WHERE imported.`source_server`='dragon14.teamobi.com:18001'
 AND s.`item_type` IN (18,21) AND t.`TYPE` IN (18,21)
 AND t.`NAME`=s.`name` AND t.`gender`=s.`gender` AND t.`icon_id`=s.`icon_id`
 AND NOT EXISTS (SELECT 1 FROM `mini_pet` old WHERE old.`id_temp`=t.`id`);
INSERT IGNORE INTO `visual_mini_target`
SELECT t.`id`, m.`source_item_id`
FROM `visual_mini_source` m
JOIN `reference_item_template` s ON s.`id`=m.`source_item_id` AND s.`source_server`='dragon14.teamobi.com:18001'
JOIN `item_template` t ON t.`id`=m.`source_item_id`
WHERE s.`item_type` IN (18,21) AND t.`TYPE` IN (18,21)
 AND t.`NAME`=s.`name` AND t.`gender`=s.`gender` AND t.`icon_id`=s.`icon_id`
 AND NOT EXISTS (SELECT 1 FROM `mini_pet` old WHERE old.`id_temp`=t.`id`);
CREATE TEMPORARY TABLE `visual_mini_needed` AS
 SELECT m.`head` AS `source_part_id` FROM `visual_mini_source` m JOIN `visual_mini_target` t ON t.`source_item_id`=m.`source_item_id`
 UNION SELECT m.`body` FROM `visual_mini_source` m JOIN `visual_mini_target` t ON t.`source_item_id`=m.`source_item_id`
 UNION SELECT m.`leg` FROM `visual_mini_source` m JOIN `visual_mini_target` t ON t.`source_item_id`=m.`source_item_id`;
CREATE TEMPORARY TABLE `visual_mini_resolved` (`source_part_id` INT PRIMARY KEY, `part_id` INT NOT NULL);
INSERT IGNORE INTO `visual_mini_resolved`
SELECT n.`source_part_id`, a.`part_id`
FROM `visual_mini_needed` n
JOIN `admin_part_alias` a ON a.`source_server`='dragon14.teamobi.com:18001' AND a.`source_part_id`=n.`source_part_id`
JOIN `reference_part` s ON s.`source_server`=a.`source_server` AND s.`id`=n.`source_part_id`
JOIN `part` p ON p.`id`=a.`part_id` AND p.`TYPE`=s.`part_type` AND BINARY p.`DATA`=BINARY s.`data`;
INSERT IGNORE INTO `visual_mini_resolved`
SELECT n.`source_part_id`, p.`id` FROM `visual_mini_needed` n
JOIN `reference_part` s ON s.`source_server`='dragon14.teamobi.com:18001' AND s.`id`=n.`source_part_id`
JOIN `part` p ON p.`id`=n.`source_part_id` AND p.`TYPE`=s.`part_type` AND BINARY p.`DATA`=BINARY s.`data`;
INSERT IGNORE INTO `visual_mini_resolved`
SELECT n.`source_part_id`, MIN(p.`id`) FROM `visual_mini_needed` n
JOIN `reference_part` s ON s.`source_server`='dragon14.teamobi.com:18001' AND s.`id`=n.`source_part_id`
JOIN `part` p ON p.`TYPE`=s.`part_type` AND BINARY p.`DATA`=BINARY s.`data`
GROUP BY n.`source_part_id`;
SET @visual_mini_start=(SELECT COALESCE(MAX(`id`),-1)+1 FROM `part`);
CREATE TEMPORARY TABLE `visual_mini_new` AS
SELECT n.`source_part_id`, @visual_mini_start+ROW_NUMBER() OVER (ORDER BY n.`source_part_id`)-1 AS `part_id`
FROM `visual_mini_needed` n LEFT JOIN `visual_mini_resolved` p ON p.`source_part_id`=n.`source_part_id`
WHERE p.`source_part_id` IS NULL;
CREATE TEMPORARY TABLE `visual_mini_integrity` (`id` INT PRIMARY KEY);
INSERT INTO `visual_mini_integrity` VALUES (1);
INSERT INTO `visual_mini_integrity` SELECT 1 WHERE EXISTS (SELECT 1 FROM `visual_mini_new` WHERE `part_id`>32767)
 OR EXISTS (SELECT 1 FROM `visual_mini_needed` n LEFT JOIN `reference_part` s
 ON s.`source_server`='dragon14.teamobi.com:18001' AND s.`id`=n.`source_part_id` WHERE s.`id` IS NULL);
INSERT INTO `part` (`id`,`TYPE`,`DATA`)
SELECT fresh.`part_id`,s.`part_type`,s.`data` FROM `visual_mini_new` fresh
JOIN `reference_part` s ON s.`source_server`='dragon14.teamobi.com:18001' AND s.`id`=fresh.`source_part_id`;
INSERT INTO `admin_part_alias` (`source_server`,`source_part_id`,`part_id`)
SELECT 'dragon14.teamobi.com:18001',`source_part_id`,`part_id` FROM `visual_mini_new` WHERE 1=1
ON DUPLICATE KEY UPDATE `part_id`=VALUES(`part_id`);
INSERT INTO `visual_mini_resolved` SELECT `source_part_id`,`part_id` FROM `visual_mini_new`;
INSERT INTO `mini_pet` (`id_temp`,`head`,`body`,`leg`)
SELECT t.`item_id`,h.`part_id`,b.`part_id`,l.`part_id` FROM `visual_mini_target` t
JOIN `visual_mini_source` m ON m.`source_item_id`=t.`source_item_id`
JOIN `visual_mini_resolved` h ON h.`source_part_id`=m.`head`
JOIN `visual_mini_resolved` b ON b.`source_part_id`=m.`body`
JOIN `visual_mini_resolved` l ON l.`source_part_id`=m.`leg`
WHERE NOT EXISTS (SELECT 1 FROM `mini_pet` old WHERE old.`id_temp`=t.`item_id`);
UPDATE `admin_editor_state` SET `data_version`=CASE WHEN `data_version`>=120 THEN 1 ELSE `data_version`+1 END
WHERE `id`=1 AND EXISTS (SELECT 1 FROM `visual_mini_target`);
DROP TEMPORARY TABLE `visual_mini_integrity`;
DROP TEMPORARY TABLE `visual_mini_new`;
DROP TEMPORARY TABLE `visual_mini_resolved`;
DROP TEMPORARY TABLE `visual_mini_needed`;
DROP TEMPORARY TABLE `visual_mini_target`;
DROP TEMPORARY TABLE `visual_mini_source`;
