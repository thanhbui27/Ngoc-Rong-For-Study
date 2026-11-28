-- Map verified server-14 costume sprites to this BE without assuming that
-- source item or part IDs equal runtime IDs. Source part definitions come from
-- V7 reference_part; imported item identities come from V9 and V17.
-- Sprite PNGs 17410-17470 for Champa/Belmod are 1x1 placeholders in the
-- captured resources. Their part definitions are retained for future art.
CREATE TEMPORARY TABLE `costume_source_mapping` (
  `source_item_id` int NOT NULL PRIMARY KEY,
  `head` int NOT NULL,
  `body` int NOT NULL,
  `leg` int NOT NULL
);
INSERT INTO `costume_source_mapping` (`source_item_id`, `head`, `body`, `leg`) VALUES
(196, 101, -1, -1),
(197, 102, -1, -1),
(198, 103, -1, -1),
(199, 104, -1, -1),
(200, 105, -1, -1),
(201, 106, -1, -1),
(202, 107, -1, -1),
(203, 108, -1, -1),
(204, 109, -1, -1),
(205, 110, -1, -1),
(206, 112, -1, -1),
(207, 111, -1, -1),
(208, 113, -1, -1),
(209, 0, -1, -1),
(210, 0, -1, -1),
(227, 127, -1, -1),
(228, 128, -1, -1),
(229, 126, -1, -1),
(282, 98, 99, 100),
(283, 77, 78, 79),
(284, 92, 93, 94),
(285, 89, 90, 91),
(286, 86, 87, 88),
(287, 83, 84, 85),
(288, 159, 160, 161),
(289, 162, 163, 164),
(290, 171, 172, 173),
(291, 123, 124, 125),
(292, 174, 175, 176),
(386, 277, -1, -1),
(387, 276, -1, -1),
(388, 278, -1, -1),
(389, 274, -1, -1),
(390, 273, -1, -1),
(391, 275, -1, -1),
(392, 280, -1, -1),
(393, 279, -1, -1),
(394, 281, -1, -1),
(405, 183, 184, 185),
(406, 186, 187, 188),
(407, 189, 190, 191),
(408, 310, 307, 308),
(409, 309, 307, 308),
(410, 306, 307, 308),
(411, 240, 241, 242),
(412, 64, -1, -1),
(413, 30, -1, -1),
(414, 31, -1, -1),
(415, 9, -1, -1),
(416, 29, -1, -1),
(417, 32, -1, -1),
(418, 6, -1, -1),
(419, 27, -1, -1),
(420, 28, -1, -1),
(421, 314, 315, 316),
(422, 311, 312, 313),
(423, 341, 342, 343),
(424, 329, 330, 331),
(425, 332, 333, 334),
(426, 335, 336, 337),
(427, 323, 324, 325),
(428, 326, 327, 328),
(429, 168, 169, 170),
(430, 174, 175, 176),
(431, 171, 172, 173),
(432, 177, 178, 179),
(433, 180, 181, 182),
(448, 353, 354, 355),
(449, 377, 378, 379),
(450, 350, 351, 352),
(451, 344, 345, 346),
(452, 347, 348, 349),
(455, 400, 401, 402),
(458, 359, 360, 361),
(461, 394, 395, 396),
(463, 403, 404, 405),
(464, 409, 410, 411),
(524, 249, 250, 251),
(525, 255, 256, 257),
(526, 228, 229, 230),
(527, 231, 232, 233),
(528, 234, 235, 236),
(544, 457, 458, 459),
(545, 460, 458, 459),
(546, 461, 458, 459),
(547, 462, 463, 464),
(548, 465, 466, 464),
(549, 264, 265, 266),
(550, 252, 253, 254),
(551, 246, 247, 248),
(552, 261, 262, 263),
(575, 451, 452, 453),
(576, 415, 416, 417),
(577, 418, 419, 420),
(578, 297, 298, 299),
(580, 310, 307, 308),
(581, 309, 307, 308),
(582, 306, 307, 308),
(583, 240, 241, 242),
(584, 409, 410, 411),
(586, 350, 351, 352),
(587, 344, 345, 346),
(588, 353, 354, 355),
(591, 542, 523, 524),
(592, 0, 523, 524),
(593, 128, 523, 524),
(594, 126, 523, 524),
(598, 561, -1, -1),
(599, 560, -1, -1),
(600, 562, -1, -1),
(601, 566, 567, 568),
(602, 570, 571, 572),
(603, 563, 564, 565),
(604, 569, 472, 473),
(605, 536, 476, 477),
(606, 538, 474, 475),
(607, 371, 372, 373),
(608, 397, 398, 399),
(609, 517, 518, 519),
(612, 573, 574, 575),
(613, 579, 580, 581),
(614, 576, 577, 578),
(615, 177, 178, 179),
(616, 168, 169, 170),
(617, 180, 181, 182),
(618, 582, 583, 584),
(619, 585, 586, 587),
(620, 588, 589, 590),
(621, 591, 592, 593),
(622, 606, 607, 608),
(623, 600, 601, 602),
(624, 594, 595, 596),
(625, 597, 598, 599),
(626, 603, 604, 605),
(628, -1, -1, -1),
(629, 502, 503, 504),
(630, 493, 494, 495),
(631, 496, 497, 498),
(632, 499, 500, 501),
(633, 237, 238, 239),
(634, 243, 244, 245),
(635, 612, 613, 614),
(636, 615, 616, 617),
(637, 618, 619, 620),
(639, 627, 628, 629),
(640, 630, 631, 632),
(641, 633, 634, 635),
(642, 651, 652, 653),
(643, 654, 655, 656),
(644, 1305, -1, -1),
(645, 1307, -1, -1),
(646, 1306, -1, -1),
(647, 642, 643, 644),
(675, 696, 697, 698),
(676, 684, 685, 686),
(677, 693, 694, 695),
(678, 687, 688, 689),
(679, 681, 682, 683),
(680, 690, 691, 692),
(681, 678, 679, 680),
(682, 112, -1, -1),
(683, 111, -1, -1),
(684, 113, -1, -1),
(685, 101, -1, -1),
(686, 103, -1, -1),
(687, 107, -1, -1),
(688, 106, -1, -1),
(689, 108, -1, -1),
(690, 110, -1, -1),
(710, 554, 555, 556),
(711, 356, 357, 358),
(719, 724, 725, 726),
(724, 736, 737, 738),
(729, 639, 640, 641),
(730, 745, 746, 747),
(731, 748, 749, 750),
(732, 751, 752, 753),
(738, 742, 743, 744),
(739, 754, 755, 756),
(742, 757, 758, 759),
(754, 769, -1, -1),
(755, 771, -1, -1),
(756, 770, -1, -1),
(760, 772, 773, 774),
(761, 775, -1, -1),
(762, 777, -1, -1),
(763, 776, -1, -1),
(765, 427, 428, 429),
(806, 790, 791, 792),
(819, 802, 803, 804),
(824, 805, 806, 807),
(825, 809, 806, 807),
(826, 808, 806, 807),
(827, 810, 811, 812),
(843, 816, 817, 818),
(844, 822, 823, 824),
(845, 819, 820, 821),
(846, 825, -1, -1),
(847, 827, -1, -1),
(848, 826, -1, -1),
(853, 833, 834, 835),
(854, 837, 834, 835),
(855, 836, 834, 835),
(856, 828, 829, 830),
(857, 832, 829, 830),
(858, 831, 829, 830),
(860, 841, 842, 843),
(862, 844, 845, 846),
(863, 850, 851, 852),
(864, 847, 848, 849),
(866, 855, -1, -1),
(867, 854, -1, -1),
(868, 853, -1, -1),
(872, 856, -1, -1),
(873, 857, -1, -1),
(875, 858, 859, 860),
(876, 861, 862, 863),
(877, 864, 865, 866),
(878, 709, 710, 711),
(879, 712, 713, 714),
(883, 879, 880, 881),
(884, 520, 521, 522),
(885, 888, 889, 890),
(894, 900, -1, -1),
(895, 902, -1, -1),
(896, 901, -1, -1),
(898, 903, 904, 905),
(904, 906, 880, 881),
(905, 910, 911, 912),
(906, 907, 908, 909),
(907, 913, 914, 915),
(911, 542, 523, 524),
(912, 916, 917, 918),
(913, 919, 920, 921),
(914, 922, 923, 924),
(922, 937, 938, 939),
(923, 943, 944, 945),
(924, 940, 941, 942),
(932, 946, 947, 948),
(937, 950, 951, 952),
(938, 956, 957, 958),
(939, 962, 963, 964),
(940, 959, 960, 961),
(941, 965, -1, -1),
(945, 975, 976, 977),
(946, 979, -1, -1),
(947, 981, -1, -1),
(948, 983, 984, 985),
(951, 992, 976, 977),
(952, 986, 987, 988),
(953, 989, 990, 991),
(957, 997, 998, 999),
(958, 1003, 1004, 1005),
(959, 1000, 1001, 1002),
(968, 1029, 1047, 1048),
(969, 1030, 1047, 1048),
(970, 1031, 1047, 1048),
(971, 1032, 1047, 1048),
(972, 1042, 1047, 1048),
(973, 1033, 1034, 1035),
(974, 1036, 1037, 1038),
(975, 1039, 1040, 1041),
(976, 1043, 1044, 1045),
(977, 1046, 1047, 1048),
(978, 1049, 1047, 1048),
(985, 1024, 1025, 1026),
(986, 1021, 1022, 1023),
(989, 1053, 1054, 1055),
(990, 1056, 1057, 1058),
(991, 1059, 1060, 1061),
(1010, 1065, 1066, 1067),
(1011, 1068, 1069, 1070),
(1012, 1071, 1072, 1073),
(1018, 1080, 1081, 1082),
(1019, 1086, 1087, 1088),
(1020, 1083, 1084, 1085),
(1041, 1095, 1096, 1097),
(1042, 1098, 1099, 1100),
(1043, 1101, 1102, 1103),
(1063, 1104, 1105, 1106),
(1064, 1114, 1115, 1116),
(1065, 1109, 1110, 1111),
(1087, 1119, 1120, 1121),
(1088, 1122, 1123, 1124),
(1089, 1131, 1132, 1133),
(1090, 1125, 1126, 1127),
(1091, 1128, 1129, 1130),
(1103, 1140, 1141, 1142),
(1104, 1146, 1147, 1148),
(1105, 1149, 1150, 1151),
(1106, 1152, 1153, 1154),
(1145, 1167, -1, -1),
(1146, 1167, -1, -1),
(1147, 1167, -1, -1),
(1148, 1168, -1, -1),
(1155, 1170, 1171, 1172),
(1156, 1173, 1174, 1175),
(1157, 1176, 1177, 1178),
(1174, 1186, 1190, 1191),
(1175, 1188, 1196, 1197),
(1176, 1187, 1193, 1194),
(1198, 1186, -1, -1),
(1199, 1188, -1, -1),
(1200, 1187, -1, -1),
(1201, 1198, 1199, 1200),
(1205, 1207, 1208, 1209),
(1208, 1213, 1214, 1215),
(1209, 1216, 1214, 1215),
(1210, 1217, 1214, 1215),
(1234, 1239, 1240, 1241),
(1235, 1236, 1237, 1238),
(1236, 1242, 1243, 1244),
(1255, 1264, 1265, 1266),
(1257, 1273, 1271, 1272),
(1265, 1279, 1280, 1281),
(1266, 1164, -1, -1),
(1267, 1274, -1, -1),
(1268, 1164, -1, -1),
(1269, 1165, -1, -1),
(1270, 1275, -1, -1),
(1271, 1165, -1, -1),
(1276, 1282, 1283, 1284),
(1277, 1293, 1294, 1295),
(1302, 1291, 1292, -1),
(1309, 1296, 1297, 1298),
(1362, 1308, 1309, 1310),
(1371, 1317, 1318, 1319),
(1378, 1320, 1321, 1322),
(1379, 1323, 1324, 1325),
(1380, 1326, 1327, 1328),
(1381, 1338, 1339, 1340),
(1383, 1332, 1333, 1334),
(1384, 1335, 1336, 1337),
(1385, 1314, 1315, 1316),
(1389, 1329, -1, -1),
(1390, 1331, -1, -1),
(1391, 1330, -1, -1),
(1396, 636, 637, 638),
(1424, 1344, 1345, 1346),
(1436, 1350, 1351, 1352),
(1437, 1353, 1354, 1355),
(1442, 1362, 1363, 1364),
(1450, 1359, 1360, 1361),
(1454, 553, 551, 552),
(1469, 1374, -1, -1),
(1470, 1376, -1, -1),
(1471, 1375, -1, -1),
(1476, 1380, 1381, 1382),
(1483, 1395, 1396, 1397),
(1484, 1386, 1387, 1388),
(1485, 1392, 1393, 1394),
(1486, 1389, 1390, 1391),
(1498, 1404, 1405, 1406),
(1499, 1410, 1411, 1412),
(1500, 1407, 1408, 1409),
(1503, 1413, 1414, 1415),
(1504, 1419, 1420, 1421),
(1512, 1416, 1417, 1418),
(1553, 1431, 1432, 1433),
(1557, 1434, 1435, 1436),
(1566, 888, 889, 890),
(1567, 1440, 1441, 1442),
(1587, 1449, 1450, 1451),
(1588, 0, 1, 2),
(1589, 101, -1, -1),
(1590, 1458, 1459, 1460),
(1593, 1469, 1459, 1460),
(1595, 1456, 1459, 1460),
(1599, 1476, 1477, 1478),
(1600, 1479, 1480, 1481),
(1601, 1482, 1483, 1484),
(1602, 1485, 1486, 1487),
(1604, 1482, 1483, 1484),
(1632, 1520, 1521, 1522),
(1657, 1543, 1544, 1545),
(1658, 1531, -1, -1),
(1659, 1535, -1, -1),
(1660, 1533, -1, -1),
(1661, 1537, -1, -1),
(1662, 1541, -1, -1),
(1663, 1539, -1, -1),
(1667, 1547, 1548, 1549),
(1674, 1555, 1556, 1557),
(1684, 1566, 1567, 1568),
(1685, 1569, 1570, 1571),
(1693, 1575, 1576, 1577),
(1697, 1580, 1581, 1582),
(1698, 1583, 1584, 1585),
(1700, 1586, 1587, 1588),
(1705, 1589, 1590, 1591),
(1708, 1594, 1595, 1596),
(1709, 1597, 1595, 1596),
(1710, 1605, 1606, 1607),
(1723, 371, 372, 373),
(1732, 1627, 1628, 1629),
(1741, 1636, 1637, 1638),
(1742, 1630, 1632, 1633),
(1743, 1634, 1632, 1633),
(1744, 1639, 1632, 1633),
(1745, 1643, 1642, 1638),
(1746, 1646, 1648, 1649),
(1762, 1656, 1657, 1658),
(1763, 1659, 1660, 1661),
(1764, 1662, 1663, 1664),
(1775, 1679, 1680, 1681),
(1777, 1682, 1685, 1681),
(1778, 1686, 1687, 1688),
(1785, 1198, 1199, 1200),
(1795, 1707, 1708, 1709),
(1797, 1710, 1711, 1712),
(1800, 371, 372, 373),
(1803, 1721, 1722, 1723),
(1805, 1724, 1725, 1726),
(1810, 1727, 1728, 1729),
(1811, 1730, 1731, 1732),
(1826, 1754, 1755, 1756),
(1827, 1757, 1758, 1759),
(1829, 1762, 1763, 1764),
(1832, 1772, 1773, 1774),
(1839, 1781, 1782, 1783),
(1849, 1781, 1782, 1783),
(1853, 1793, 1794, 1795),
(1854, 1796, 1797, 1798),
(1865, 1804, 1805, 1806),
(1866, 1809, 1810, 1811),
(1867, 1814, 1815, 1816),
(1869, 1817, 1815, 1816),
(1879, 1835, 1836, 1837),
(1880, 1838, 1839, 1840),
(1886, 1844, 1845, 1846),
(1889, 1850, 1851, 1852),
(1905, 1861, 1862, 1863),
(1906, 508, 509, 510),
(1907, 511, 512, 513),
(1908, 1864, 1865, 1866),
(1911, 1867, 1868, 1869),
(1912, 1870, 1871, 1872),
(1913, 1873, 1874, 1875),
(1919, 1879, 1880, 1881),
(1921, 1882, 1883, 1884),
(1926, 1885, 1886, 1887),
(1931, 1891, 1892, 1893),
(1933, 1894, 1895, 1896),
(1934, 1897, 1898, 1899),
(1937, 1903, 1904, 1905),
(1946, 1912, 1913, 1914),
(1949, 1915, 1916, 1917),
(1952, 1918, 1919, 1920),
(1955, 1927, 1928, 1929),
(1957, 1933, 1934, 1935),
(1968, 1942, 1943, 1944),
(1972, 1945, 1946, 1947),
(1982, 1965, 1966, 1967),
(1992, 802, 803, 804),
(1996, 1968, 1969, 1970),
(1997, 1971, 1972, 1973),
(1999, 1974, 1975, 1976),
(2005, 1977, 1978, 1979),
(2020, 1994, 1995, 1996),
(2026, 2000, 2001, 2002),
(2027, 2003, 2004, 2005),
(2033, 2006, 2007, 2008),
(2039, 2012, 2013, 2014),
(2043, 2015, 2016, 2017),
(2048, 2018, 2019, 2020),
(2049, 2021, 2022, 2023),
(2050, 2024, 2025, 2026),
(2051, 2027, 2028, 2029),
(2052, 2030, 2031, 2032),
(2053, 2033, 2034, 2035),
(2062, 2039, 2040, 2041),
(2063, 2042, 2043, 2044),
(2075, 2053, 2054, 2055),
(2082, 2061, 2062, 2063),
(2085, 2064, 2065, 2066),
(2086, 2070, 2071, 2072),
(2091, 2067, 2068, 2069),
(2093, 2073, 2074, 2075),
(2099, 2079, 2080, 2081),
(2104, 2082, 2083, 2084),
(2108, 2094, 2095, 2096);

CREATE TABLE IF NOT EXISTS `admin_part_alias` (
  `source_server` varchar(100) NOT NULL,
  `source_part_id` int NOT NULL,
  `part_id` int NOT NULL,
  PRIMARY KEY (`source_server`, `source_part_id`),
  UNIQUE KEY `uq_part_id` (`part_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TEMPORARY TABLE `costume_parts_needed` AS
SELECT `head` AS `source_part_id` FROM `costume_source_mapping` WHERE `head` >= 0
UNION SELECT `body` FROM `costume_source_mapping` WHERE `body` >= 0
UNION SELECT `leg` FROM `costume_source_mapping` WHERE `leg` >= 0;
CREATE TEMPORARY TABLE `costume_part_resolved` (
  `source_part_id` int NOT NULL PRIMARY KEY,
  `part_id` int NOT NULL
);

-- Reuse an earlier editor import only when its type and frames still match.
INSERT IGNORE INTO `costume_part_resolved` (`source_part_id`, `part_id`)
SELECT needed.`source_part_id`, alias.`part_id`
FROM `costume_parts_needed` needed
JOIN `admin_part_alias` alias
  ON alias.`source_server` = 'dragon14.teamobi.com:18001'
 AND alias.`source_part_id` = needed.`source_part_id`
JOIN `reference_part` source_part
  ON source_part.`source_server` = alias.`source_server`
 AND source_part.`id` = needed.`source_part_id`
JOIN `part` local_part ON local_part.`id` = alias.`part_id`
 AND local_part.`TYPE` = source_part.`part_type`
 AND BINARY local_part.`DATA` = BINARY source_part.`data`;

-- Most early part IDs already agree with the captured client.
INSERT IGNORE INTO `costume_part_resolved` (`source_part_id`, `part_id`)
SELECT needed.`source_part_id`, local_part.`id`
FROM `costume_parts_needed` needed
JOIN `reference_part` source_part
  ON source_part.`source_server` = 'dragon14.teamobi.com:18001'
 AND source_part.`id` = needed.`source_part_id`
JOIN `part` local_part ON local_part.`id` = needed.`source_part_id`
 AND local_part.`TYPE` = source_part.`part_type`
 AND BINARY local_part.`DATA` = BINARY source_part.`data`;

-- A matching frame set under another local ID can be shared too.
INSERT IGNORE INTO `costume_part_resolved` (`source_part_id`, `part_id`)
SELECT needed.`source_part_id`, MIN(local_part.`id`)
FROM `costume_parts_needed` needed
JOIN `reference_part` source_part
  ON source_part.`source_server` = 'dragon14.teamobi.com:18001'
 AND source_part.`id` = needed.`source_part_id`
JOIN `part` local_part ON local_part.`TYPE` = source_part.`part_type`
 AND BINARY local_part.`DATA` = BINARY source_part.`data`
GROUP BY needed.`source_part_id`;

-- Allocate new runtime IDs for the remaining observed part definitions.
SET @costume_part_start = (SELECT COALESCE(MAX(`id`), -1) + 1 FROM `part`);
CREATE TEMPORARY TABLE `costume_part_new` AS
SELECT needed.`source_part_id`,
       @costume_part_start + ROW_NUMBER() OVER (ORDER BY needed.`source_part_id`) - 1 AS `part_id`
FROM `costume_parts_needed` needed
LEFT JOIN `costume_part_resolved` resolved
  ON resolved.`source_part_id` = needed.`source_part_id`
WHERE resolved.`source_part_id` IS NULL;
INSERT INTO `part` (`id`, `TYPE`, `DATA`)
SELECT fresh.`part_id`, source_part.`part_type`, source_part.`data`
FROM `costume_part_new` fresh
JOIN `reference_part` source_part
  ON source_part.`source_server` = 'dragon14.teamobi.com:18001'
 AND source_part.`id` = fresh.`source_part_id`;
INSERT INTO `admin_part_alias` (`source_server`, `source_part_id`, `part_id`)
SELECT 'dragon14.teamobi.com:18001', `source_part_id`, `part_id`
FROM `costume_part_new`
WHERE 1 = 1
ON DUPLICATE KEY UPDATE `part_id` = VALUES(`part_id`);
INSERT INTO `costume_part_resolved` (`source_part_id`, `part_id`)
SELECT `source_part_id`, `part_id` FROM `costume_part_new`;

CREATE TEMPORARY TABLE `costume_item_target` (
  `item_id` int NOT NULL PRIMARY KEY,
  `source_item_id` int NOT NULL
);
-- Imported source items have new runtime IDs because old IDs can mean
-- completely different items in this BE.
INSERT IGNORE INTO `costume_item_target` (`item_id`, `source_item_id`)
SELECT imported.`item_id`, mapped.`source_item_id`
FROM `costume_source_mapping` mapped
JOIN `admin_catalog_item_source` imported
  ON imported.`source_server` = 'dragon14.teamobi.com:18001'
 AND imported.`source_item_id` = mapped.`source_item_id`
JOIN `reference_item_template` source_item
  ON source_item.`source_server` = imported.`source_server`
 AND source_item.`id` = mapped.`source_item_id`
 AND source_item.`item_type` = 5
JOIN `item_template` local_item ON local_item.`id` = imported.`item_id`
 AND local_item.`TYPE` = 5
 AND local_item.`gender` = source_item.`gender`
 AND BINARY local_item.`NAME` = BINARY source_item.`name`
 AND local_item.`icon_id` = source_item.`icon_id`;

-- Also correct legacy items whose ID, identity, and icon already match.
INSERT IGNORE INTO `costume_item_target` (`item_id`, `source_item_id`)
SELECT local_item.`id`, mapped.`source_item_id`
FROM `costume_source_mapping` mapped
JOIN `reference_item_template` source_item
  ON source_item.`source_server` = 'dragon14.teamobi.com:18001'
 AND source_item.`id` = mapped.`source_item_id`
 AND source_item.`item_type` = 5
JOIN `item_template` local_item ON local_item.`id` = mapped.`source_item_id`
 AND local_item.`TYPE` = 5
 AND local_item.`gender` = source_item.`gender`
 AND BINARY local_item.`NAME` = BINARY source_item.`name`
 AND local_item.`icon_id` = source_item.`icon_id`;

INSERT INTO `cai_trang` (`id_temp`, `head`, `body`, `leg`, `bag`)
SELECT target.`item_id`, head_part.`part_id`,
       COALESCE(body_part.`part_id`, -1), COALESCE(leg_part.`part_id`, -1), -1
FROM `costume_item_target` target
JOIN `costume_source_mapping` mapped ON mapped.`source_item_id` = target.`source_item_id`
JOIN `costume_part_resolved` head_part ON head_part.`source_part_id` = mapped.`head`
LEFT JOIN `costume_part_resolved` body_part ON body_part.`source_part_id` = mapped.`body`
LEFT JOIN `costume_part_resolved` leg_part ON leg_part.`source_part_id` = mapped.`leg`
WHERE (mapped.`body` = -1 OR body_part.`part_id` IS NOT NULL)
  AND (mapped.`leg` = -1 OR leg_part.`part_id` IS NOT NULL)
ON DUPLICATE KEY UPDATE
  `head` = VALUES(`head`),
  `body` = VALUES(`body`),
  `leg` = VALUES(`leg`);

DROP TEMPORARY TABLE `costume_item_target`;
DROP TEMPORARY TABLE `costume_part_new`;
DROP TEMPORARY TABLE `costume_part_resolved`;
DROP TEMPORARY TABLE `costume_parts_needed`;
DROP TEMPORARY TABLE `costume_source_mapping`;
