# Frame Xên xanh theo hành động Xên đỏ

Các PNG ở đây dùng **màu và chi tiết gốc của Xên xanh** (ảnh nguồn 2407–2437). Chúng được ghép thành hành động tương ứng bộ Xên đỏ 17125–17134. Đây là PNG x4, nền trong suốt.

| Vị trí MiniPet | Ảnh xanh | Hành động | Ảnh đỏ tương ứng |
| --- | --- | --- | ---: |
| Thân 01 | `body-01-dung.png` | Đứng, đầu và thân | 17125 |
| Chân 00 | `leg-00-bay.png` | Bay | 17128 |
| Chân 01 | `leg-01-chan-dung.png` | Chân đứng riêng | 17126 |
| Chân 02–06 | `leg-02-chay.png` … `leg-06-chay.png` | Chạy | 17127–17131 |
| Chân 07 | `leg-07-nhay.png` | Nhảy | 17132 |
| Chân 08 | `leg-08-roi.png` | Rơi | 17133 |
| Icon | `icon-dau.png` | Đầu | 17134 |

`leg-00-bay.png` và `leg-03-chay.png` dùng cùng dáng, đúng như part Xên đỏ dùng ảnh 17128 ở cả hai vị trí. Đầu MiniPet, các frame thân khác, và chân 09–13 có thể dùng ảnh trống #2955 theo cấu trúc part Xên đỏ.

Các file này đã sẵn để dùng trong Part Studio.

## Image ID đã thêm vào server

Ảnh đã được chép vào `Server/resources/normal/image/{1,2,3,4}/icon/`. x4 giữ nguyên PNG nguồn; x1, x2, x3 được thu bằng nearest neighbor.

| Image ID | Ảnh | Vị trí |
| ---: | --- | --- |
| 32582 | `body-01-dung.png` | Thân 01 |
| 32583 | `leg-01-chan-dung.png` | Chân 01 |
| 32584 | `leg-02-chay.png` | Chân 02 |
| 32585 | `leg-03-chay.png` | Chân 00 và 03 |
| 32586 | `leg-04-chay.png` | Chân 04 |
| 32587 | `leg-05-chay.png` | Chân 05 |
| 32588 | `leg-06-chay.png` | Chân 06 |
| 32589 | `leg-07-nhay.png` | Chân 07 |
| 32590 | `leg-08-roi.png` | Chân 08 |
| 32591 | `icon-dau.png` | Icon item |

Các frame đầu và thân/chân còn lại vẫn dùng ảnh trống #2955 như bộ đỏ. Chưa tạo part hoặc gán vào item trong SQL.
