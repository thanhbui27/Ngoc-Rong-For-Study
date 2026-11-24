# Part Studio cho BE Ngọc Rồng

Đây là trang cục bộ; nút **Kết nối server** dùng tài khoản có `is_admin=1`
để xác thực với action `-126` trong `Controller` của game server. Các thao tác
đọc/ghi SQL chạy **trên game server** với DB trong `server.properties` của BE.
Máy chạy editor chỉ cần địa chỉ IP và cổng game, không cần cổng MariaDB.
Phải build và triển khai BE có action này lên server trước; cổng game của bản
cũ sẽ không hiểu lệnh. Công cụ không xuất SQL. Mỗi lần bấm
**Lưu vào SQL**, API kiểm tra `item_template`, `cai_trang` hoặc `mini_pet`,
`part`, loại và số frame, giới hạn byte/short rồi ghi trong một transaction.
Part bị sửa được sao chép sang ID mới; part cũ và item khác giữ nguyên.

## Chạy trên Windows

Trên Windows bấm đúp `PartStudio.cmd` ở thư mục repo, nhập IP/cổng game (Enter
để dùng `103.116.52.124:14445`), rồi đăng nhập bằng **tài khoản admin** ngay
trên trang. Trang sẽ tự mở trong trình duyệt. Nếu muốn chạy từ PowerShell:

```powershell
& .\tools\part-editor\run.ps1
```

Script dùng JDK và JAR phụ thuộc sẵn có trong `Server/target`. Build BE mới
trước khi triển khai và chạy editor. Nó in URL
`http://127.0.0.1:8182/?token=...`; mở đúng URL đó. HTTP chỉ lắng nghe trên
loopback và mọi action cần token ngẫu nhiên của phiên chạy. Không nhập tài
khoản admin vào file cấu hình hay URL.

1. Chọn **Cải trang** hoặc **Pet** để tải toàn bộ item tương ứng từ DB; chọn
   một item để xem mapping và từng part.
2. Chọn part BE theo ID, hoặc part S14 theo ID. Khi nạp part S14, server so
   từng ảnh x1–x4 với BE và tạo image ID mới cho ảnh bị trùng nhưng khác nội
   dung. Ảnh nguồn thiếu phải được nhập thủ công trước khi lưu part đó.
   Part S14 được đọc từ `Server/resources/reference/server14/part.bin` trên
   máy chạy editor; ảnh gốc cần ở thư mục ngang repo
   `NRO-server15-assets/image/zoomN/icon/`. Khi nạp part tham chiếu, editor
   gửi ảnh nguồn tới action để server so sánh và cấp ID mới nếu cần.
3. Với part chưa có, nhấn **Tạo frame**, tải PNG vào từng hàng. Ảnh x2–x4
   được nhân gần nhất từ PNG x1. **Tự căn** đề xuất dx/dy từ vùng ảnh có alpha
   so với frame mẫu 0/1/2 của Unity; chọn từng frame và kéo trên preview để
   chỉnh lại. Unity dùng 3 frame đầu, 17 frame thân, 14 frame chân; dx/dy là
   byte có dấu trong khoảng −128…127.
4. **Lưu vào SQL** tạo hoặc cập nhật item và mapping. Nếu part đang dùng có
   toạ độ hoặc hình thay đổi, API cấp part ID mới. **Xóa mapping** bỏ ngoại
   hình nhưng giữ item; **Xóa item cuối** chỉ cho phép nếu ID là cuối bảng và
   không còn tham chiếu trong shop, sổ sưu tập hoặc túi nhân vật.
5. **Cấp ID mới cho part trùng** sao chép các part tham chiếu khác BE sang
   ID mới trong bảng `part` và ghi quan hệ nguồn ở `admin_part_alias`.
   Thao tác này không tự gắn bộ head/body/leg vào item; cần kiểm tra trong
   editor trước khi gắn.

Với item đã nhập từ server 14, editor hiện `S14 #...` và nút **Nạp part
nguồn** nếu item template có `part_id` đã biết. Những item có `part_id=-1`
không thể suy ra trọn bộ head/body/leg chỉ từ icon; cần nhập các frame PNG
và kiểm tra preview bằng mắt.

Sau khi lưu, **khởi động lại BE**. BE nạp `part` và `item_template` vào RAM
khi khởi động; phiên bản data/item được tăng trong `admin_editor_state` để
client tải lại cache. Nếu DB trên game server không chạy, trang mở được nhưng
action báo lỗi và không có thay đổi nào được ghi.

Nguồn part S14 có 2.097 bản ghi; các ảnh tải từ server 15 có cùng `part.bin`
trong lần capture, nhưng tên vật phẩm server 15 chưa được xác minh riêng.
