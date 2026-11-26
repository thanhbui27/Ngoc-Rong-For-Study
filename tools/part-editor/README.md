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
Khi tải lại trang trong lúc `PartStudio.cmd` vẫn chạy, editor tự dùng lại phiên
admin đã xác thực và nhớ tên tài khoản trong trình duyệt. Mật khẩu không được
lưu; nếu đóng rồi chạy lại công cụ thì đăng nhập lại.

Nếu ảnh bắt đầu báo `EOFException` sau khoảng 40 giây, BE đang chạy còn giữ
bộ đếm chờ đăng nhập của phiên Part Studio. Bản BE hiện tại đặt bộ đếm về 0
sau khi xác thực admin. Cần triển khai JAR BE mới và khởi động lại game server;
chỉ tải lại trang editor không thay được mã đang chạy trên game server.

1. Chọn **Cải trang** hoặc **Pet** để tải toàn bộ item tương ứng từ DB; chọn
   một item để xem mapping và từng part. Pet type 18/21 dùng ba part đầu/thân/chân
   trong `mini_pet`. Pet type 18 thiếu bộ part sẽ không dùng được cho tới khi
   cấu hình đủ; ảnh `pet_follow` cũ không còn được dùng cho type 18.
   Pet type 72 đi theo dùng icon item hoặc sprite riêng trong `pet_follow`;
   ba part đầu/thân/chân không áp dụng. Mục **Hình pet đi theo** cho chọn
   sprite trên server hoặc tải PNG, nhập số frame và xem từng frame trước khi
   lưu. Sprite là một PNG xếp các frame theo chiều dọc; rộng/cao là kích
   thước một frame ở mức x1. Nếu bỏ sprite riêng, game dùng icon item làm
   một frame tĩnh. Lưu item cập nhật `pet_follow` cùng transaction với item.
   Danh sách có bộ lọc riêng **Pet đi theo · 72** và tìm được bằng ID item.
   Nếu SQL trỏ tới icon/sprite chưa có PNG trong `resources/normal/image`,
   tool hiện dấu `?` và Image ID thiếu; có thể mở item để chọn hoặc tải ảnh mới.
2. Chọn part BE theo ID, hoặc part S14 theo ID. Ô **Nạp nhiều part** nhận 2–3
   ID cùng lúc, tự xếp theo loại đầu/thân/chân và chỉ cập nhật preview sau
   khi mọi ID đều hợp lệ. Có thể tiếp tục nạp một ID riêng ở từng nhóm. Khi
   nạp part S14, server so từng ảnh x1–x4 với BE và tạo image ID mới cho ảnh bị trùng nhưng khác nội
   dung. Ảnh nguồn thiếu phải được nhập thủ công trước khi lưu part đó.
   Part S14 được đọc từ `Server/resources/reference/server14/part.bin` trên
   máy chạy editor; ảnh gốc cần ở thư mục ngang repo
   `NRO-server15-assets/image/zoomN/icon/`. Khi nạp part tham chiếu, editor
   gửi ảnh nguồn tới action để server so sánh và cấp ID mới nếu cần.
3. Trước khi nhập PNG, chọn **PNG đem nhập là ảnh x mấy?**. Ảnh lấy từ
   `Server/resources/normal/image/4/icon` phải chọn **x4**; ảnh lấy từ
   `1/icon` phải chọn **x1**. Server giữ nguyên PNG ở mức zoom nguồn và tạo
   các mức còn lại theo kích thước logic của Unity. Mức chọn được nhớ trên máy.
   Nếu ảnh đã có trên game server, bấm **Ảnh trên server** ở icon hoặc từng
   frame; modal tải thumbnail theo trang, tìm theo Image ID hoặc lọc khoảng
   **Từ ID → Đến ID** (bao gồm cả hai đầu). Bấm **Chọn nhiều
   ảnh server** để chọn theo thứ tự frame liên tiếp, rồi bấm **Gán ảnh đã chọn**.
   Ảnh part thiếu một mức zoom sẽ không cho chọn. Chức năng này cần BE đã
   triển khai action `image-list`; chỉ mở lại Part Studio trên máy không cập
   nhật được action của BE đang chạy.
   Với part chưa có, nhấn **Tạo frame** hoặc **Chọn nhiều PNG** trong nhóm
   đầu/thân/chân. Nhiều file được xếp theo số trong tên. Part đầu nhận 2 PNG
   ở frame 00–01 và tự dùng ảnh #20 ở frame 02; chọn 3 PNG để thay ảnh mặc định.
   Part thân nhận 16 PNG ở frame 00–15; frame 16 tự dùng ảnh mặc định #16.
   Ảnh #80 không tự được gắn vào body mới. Chọn đủ 17 PNG để thay cả frame 16.
   Part chân nhận tối đa 13 PNG ở frame 00–12 và
   tự dùng ảnh #34 ở frame 13; chọn đủ 14 PNG để thay ảnh mặc định. Các frame
   còn lại để trống. Có thể chọn nhiều lần: lần sau bắt đầu ở frame chưa có ảnh
   đầu tiên và giữ các frame, tọa độ đã nhập. Chọn **Từ frame 00** hoặc vị trí
   khác để thay một đoạn ảnh cũ mà vẫn giữ các frame bên ngoài đoạn đó. Nếu
   chọn nhiều hơn số frame còn
   lại, editor báo lỗi trước khi tải ảnh; không bỏ qua file âm thầm. Kiểm tra
   preview và bấm **Tự căn**
   nếu cần. Vẫn có thể tải một PNG vào từng hàng. Bảng xem trước lấy trực tiếp
   PNG **x4** và hiển thị
   **từng frame** của Đứng 1/2, Run, Jump, Fall và các dáng còn lại;
   mỗi ô ghép đủ nhân vật.
   Với part chân chỉ có 6 PNG, editor hiện 6 hàng ảnh đã chọn; frame 13 tự dùng
   #34 và 7 vị trí giữa vẫn trống. Bấm **Xem 8 frame còn lại** để xem dáng Unity nào dùng mỗi vị trí
   và gán ID từ một frame chân đã có. Preview mặc định để trống vị trí chưa gán;
   editor không tự lặp ảnh chân vì bảng body↔chân của Unity không suy ra được
   ảnh phù hợp cho các vị trí còn thiếu.
   Thanh tải ảnh cho biết tiến độ; ảnh x4 thiếu sẽ tạm dùng x1 và báo rõ,
   còn ảnh thiếu hoàn toàn được đánh dấu trong từng frame. Khung tự điều chỉnh
   để hiện trọn nhân vật ở các dáng rộng; cỡ ảnh thực tế có thể nhỏ hơn mức
   trên thanh trượt nếu cần tránh cắt hình. Thanh cỡ ảnh cho thu nhỏ tới 0,5×;
   ảnh nguồn vẫn là PNG x4 và mức hiển thị được nhớ trên máy. Kích thước logic
   được chia nguyên theo cách `Image.getWidth/getHeight` của Unity; phần pixel
   dư ở mép PNG x4 không được vẽ. Khung nhân vật
   lớn dùng để kéo chỉnh dáng đang chọn; ba ô ảnh dưới khung cho biết Image ID
   của đầu/thân/chân và cho chọn nhanh hình cần chỉnh. Các nút trước/phát/sau
   và thanh frame cho phép xem liên tiếp 33 dáng; nút phát chạy trong nhóm hành
   động đang chọn, hoặc toàn bộ 33 dáng khi chọn Tất cả. Lưới bên cạnh cho xem
   nhanh từng frame. Ảnh đã nhập từ thư mục x4 nhưng bị coi là x1 cần nạp lại
   với mức **x4**. Các Image ID cũ được giữ nguyên để tránh ảnh hưởng dữ liệu cũ;
   sau đó căn lại tọa độ trước khi lưu item.
   Có thể bật **Hiện part mẫu cho frame trống** để căn hình; part mẫu không
   được ghi vào item. Mở **Danh sách**
   khi cần chọn item. Có thể lọc
   nhóm, đổi hướng hoặc phóng to. Giữ chuột trên pixel có hình của
   đầu/thân/chân rồi kéo để di chuyển hình; vùng trong suốt không chọn nhầm
   hình. Có thể dùng nút mũi tên để dịch 1px. Thao tác chỉ áp dụng cho các
   frame dùng cùng **Image ID** (kể cả khi ID đó xuất hiện ở part khác).
   Bảng frame vẫn cho sửa riêng từng dáng. **Tự căn** dùng ảnh
   mẫu Unity.
   Unity dùng 3 frame đầu, 17 frame thân, 14 frame chân; dx/dy là byte có dấu
   trong khoảng −128…127.
   Nút **Xóa dòng** trong từng frame đặt đúng frame đó thành `[-1,-1,-1]`;
   bấm **Lưu vào SQL** để lưu. Các frame còn lại giữ nguyên.
4. **Lưu vào SQL** tạo hoặc cập nhật item và mapping. Nếu part đang dùng có
   toạ độ hoặc hình thay đổi, API cấp part ID mới. **Xóa mapping** bỏ ngoại
   hình nhưng giữ item; **Xóa item cuối** chỉ cho phép nếu ID là cuối bảng và
   không còn tham chiếu trong shop, sổ sưu tập hoặc túi nhân vật.
   Pet type 18/21 cần đủ ba part trong `mini_pet`; API kiểm tra PNG của mọi
   Image ID được gắn vào frame trước khi lưu. Frame để `-1` là vị trí cố ý để trống.
   SQL lưu `part.DATA` thành các dòng `[imageId, dx, dy]`: loại 0 có 3 dòng,
   loại 1 có 17 dòng, loại 2 có 14 dòng. `cai_trang` hoặc `mini_pet` trỏ tới
   ba Part ID; 33 dáng Unity chỉ chọn lại các dòng này. Khi sửa item cũ,
   `item_template.part` được giữ nguyên, trừ item chỉ có đầu vốn trỏ tới
   Part ID đầu và đầu đó vừa được cấp ID mới. Item mới chỉ có đầu tự gán
   `item_template.part` bằng ID đầu; item mới đủ bộ giữ `-1` như mẫu SQL.
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
