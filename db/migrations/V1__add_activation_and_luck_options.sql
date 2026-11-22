-- Add display templates used by activation gear and the general drop-luck option.
-- INSERT IGNORE keeps the migration safe on databases initialized from the updated clean seed.
INSERT IGNORE INTO `item_option_template` (`id`, `NAME`, `TYPE`) VALUES
(251, 'Set Thần Vũ Trụ Kaio', 0),
(252, '(2 món +10 chí mạng)', 0),
(253, '(2 món giảm 10% hao HP, KI khi dùng Kaioken)', 0),
(254, '(5 món Kaioken +25% sát thương, giảm 25% hao HP, KI)', 0),
(255, 'Set Cadic M', 0),
(256, '(2 món Tự Phát Nổ +10% HP và phạm vi)', 0),
(257, '(4 món Tự Phát Nổ +10% sát thương)', 0),
(258, '(5 món Tự Phát Nổ +30% sát thương)', 0),
(259, 'Set Nail Chiến Binh Namec', 0),
(260, '(2 món +10% sát thương chí mạng)', 0),
(261, '(4 món giảm 10% hồi chiêu Masenko)', 0),
(262, '(5 món Masenko +20% sát thương, giảm 30% hồi chiêu)', 0),
(263, 'Set Gohan', 0),
(264, '(5 món +300% may mắn, +50% vàng rơi từ quái)', 0),
(265, 'Set Thần Hủy Diệt Champa', 0),
(266, '(2 món +10% sát thương lên boss)', 0),
(267, '(4 món +25% sát thương lên boss)', 0),
(268, '(5 món +50% sát thương lên boss, +20% sát thương chí mạng)', 0),
(269, '+#% tỉ lệ may mắn nhận vật phẩm từ quái', 0);
