-- Reuse visually verified costume parts for eight legacy items with matching icons.
-- Preserve names, icons and custom mappings changed after this repair was prepared.
CREATE TEMPORARY TABLE `visual_costume_repair` (
 `item_id` INT PRIMARY KEY, `name` VARCHAR(255), `icon_id` INT, `had_mapping` INT,
 `old_head` INT, `old_body` INT, `old_leg` INT, `old_bag` INT,
 `head` INT, `body` INT, `leg` INT, `bag` INT,
 `head_hash` CHAR(64), `body_hash` CHAR(64), `leg_hash` CHAR(64)
);
INSERT INTO `visual_costume_repair` VALUES
(1317,'Cải trang Super Black Goku Rose',5173,1,1294,1295,1296,-1,553,551,2156,-1,'04fa06150110b5cc4c6d75b0b1768521580698f1d8914bad836b4050cbd53dae','f6e8102441c7374b8f956f17f1013d22868080c09bd679ef2e4a383fdfe63143','b3589ff709f63dd556cbb9e5f95936ef8cfda0ef988b82da1b4765411ad43955'),
(2040,'Cải trang Black Goku',5141,0,-1,-1,-1,-1,550,551,2156,-1,'52d713e1be2e74c7bde88c64048cc063890eb74b038e9ce82c34757022fb1912','f6e8102441c7374b8f956f17f1013d22868080c09bd679ef2e4a383fdfe63143','b3589ff709f63dd556cbb9e5f95936ef8cfda0ef988b82da1b4765411ad43955'),
(2041,'Cải trang Super Black Goku',5173,0,-1,-1,-1,-1,553,551,2156,-1,'04fa06150110b5cc4c6d75b0b1768521580698f1d8914bad836b4050cbd53dae','f6e8102441c7374b8f956f17f1013d22868080c09bd679ef2e4a383fdfe63143','b3589ff709f63dd556cbb9e5f95936ef8cfda0ef988b82da1b4765411ad43955'),
(2064,'Yachirobe Xa Lánh',11494,0,-1,-1,-1,-1,2194,2195,2196,-1,'92350e95adf0d8e13fa15c9e68a6c69d20e2e94ff180b9eaea27e3aca3175baf','5b908d3ca836877b080516ad3925e553972f76db050e4a2034ab9fc1c0f5d622','a65df6301ac6902f62484f2e5451f52765b3c9b0ab624ebca6d363d39b68a9ab'),
(2098,'Goku Sjj4',20371,0,-1,-1,-1,-1,1345,1346,1347,-1,'1150cd5b38d7a1c7c41c64cf642bb739d3c9306a84fc9d80c2bb3cbd09dfc460','7e9ea04bf51181cf2b7ef1bb5eaf88d4a09fe9facc8f0cd1d3d5ef1f53c2c72e','e612a3aee1069df1cfc496a2ebe3066b9d6e5de2b2c0ee1ef5dd6e44b5ac6276'),
(1731,'CT Black Goku Rose',14336,1,-1,-1,-1,-1,1440,1438,1439,-1,'b439388d5e5413d24780b5619c7dfb324a5e1a77d284e43fad86e0c49f7ec7f2','2b5f672b236516fdcc340a53b6ab632a347c5696341d9e1152a23ed09a983d7f','d73e6beb3630b0b0da8b93cd4a378ba3fc0afa687a9b91e31a4f12872cdd859a'),
(2608,'CT Black Goku Rose',14336,0,-1,-1,-1,-1,1440,1438,1439,-1,'b439388d5e5413d24780b5619c7dfb324a5e1a77d284e43fad86e0c49f7ec7f2','2b5f672b236516fdcc340a53b6ab632a347c5696341d9e1152a23ed09a983d7f','d73e6beb3630b0b0da8b93cd4a378ba3fc0afa687a9b91e31a4f12872cdd859a'),
(2124,'Cải Trang Test',12987,1,102,523,524,-1,2274,2275,2276,-1,'8d6ac6da0a717293d154c10c9cdf5df28e7cf4e2afbee18df6faa54fd7b2cbf0','289afdb00739240aaa463f6f61986c035e689d3ee84150ef32944c08309aa1ff','767a0cab28d640c69a7204db6daba61efaacd70233a00eb4b02ef127c4d10d91');
INSERT INTO `cai_trang` (`id_temp`,`head`,`body`,`leg`,`bag`)
SELECT r.`item_id`,r.`head`,r.`body`,r.`leg`,r.`bag`
FROM `visual_costume_repair` r
JOIN `item_template` i ON i.`id`=r.`item_id` AND i.`TYPE`=5
 AND BINARY i.`NAME`=BINARY r.`name` AND i.`icon_id`=r.`icon_id`
JOIN `part` h ON h.`id`=r.`head` AND h.`TYPE`=0 AND SHA2(h.`DATA`,256)=r.`head_hash`
JOIN `part` b ON b.`id`=r.`body` AND b.`TYPE`=1 AND SHA2(b.`DATA`,256)=r.`body_hash`
JOIN `part` l ON l.`id`=r.`leg` AND l.`TYPE`=2 AND SHA2(l.`DATA`,256)=r.`leg_hash`
LEFT JOIN `cai_trang` old ON old.`id_temp`=r.`item_id`
WHERE (r.`had_mapping`=0 AND old.`id_temp` IS NULL)
 OR (r.`had_mapping`=1 AND old.`head`=r.`old_head` AND old.`body`=r.`old_body`
 AND old.`leg`=r.`old_leg` AND old.`bag`=r.`old_bag`)
ON DUPLICATE KEY UPDATE `head`=VALUES(`head`),`body`=VALUES(`body`),`leg`=VALUES(`leg`),`bag`=VALUES(`bag`);
DROP TEMPORARY TABLE `visual_costume_repair`;
