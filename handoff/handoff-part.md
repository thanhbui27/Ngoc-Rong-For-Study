# Bàn giao Part Studio — cập nhật 28/11/2026

## Cập nhật từ luồng Clone Studio

- `origin/main` đã có `a951a32e5`: Clone Studio tự gắn part sau khi clone hoặc mở bản lưu dựa trên mapping tham chiếu và toàn bộ frame khớp; giữ mapping đã lưu. Chi tiết, kiểm tra và giới hạn ở `handoff/handoff-tool-clone.md`. Thay đổi này không ghi DB từ UI clone.
- Đã push V23 (`3579a3fd6`) đối chiếu/nhập part và ghi `cai_trang`, V24 (`3c9df80a8`) upsert 487 cải trang Server 14 vào `item_template` theo ID nguồn và ghi `cai_trang`. Người dùng cho phép ghi đè item trùng ID; có thể đổi một ID pet cũ thành cải trang. V24 chưa dọn mapping `mini_pet`/`pet_follow` cũ cho ID bị ghi đè.
- **Chưa chạy hai migration trên DB thật**; lần kiểm tra chưa có MySQL Windows đang nghe hoặc CLI khả dụng. Người dùng yêu cầu **không dùng Docker**. Không báo DB đã cập nhật chỉ vì migration đã push. Cần xác định DB đích khi tiếp tục áp dụng.
- Bản clone ngoài Git ở `D:\Code\game nro\clone test` có 480 cải trang có ít nhất một part và 112 mini pet đã gắn. Bảy cải trang chỉ có icon. #2062 Champa và #2063 Belmod có part hợp lệ nhưng PNG nguồn đang là đen 1×1; xem handoff clone trước khi chẩn đoán lỗi gắn part.

Các mục bên dưới mô tả Part Studio tại lần bàn giao 27/11; thông tin HEAD/process/working tree trong đó là lịch sử, cần đọc lại trạng thái thực tế trước khi thao tác.

## Phạm vi và trạng thái

Part Studio là công cụ cục bộ để xem, tạo và sửa cải trang hoặc pet trong BE Ngọc Rồng. UI ở `tools/part-editor/index.html`; cầu nối HTTP và thao tác DB ở `Server/src/main/java/nro/tools/PartEditorServer.java`; client nói chuyện với game server ở `Server/src/main/java/nro/tools/GamePartEditorClient.java`. Hướng dẫn thao tác chi tiết nằm trong `tools/part-editor/README.md`.

Repo là `D:\Code\game nro\Folder Server`, nhánh `main`, HEAD lúc bàn giao `b099c36b8` (`update`). Không có sửa đổi chưa commit trong `tools/part-editor/` hay hai file Java của Part Studio. Working tree có thay đổi Bot Manager, `HANDOFF.md` bị xóa và thư mục `handoff/` chưa theo dõi; không stage hoặc khôi phục các file đó khi chỉ làm Part Studio.

## Chạy công cụ và kết nối

- Trên Windows, chạy `tools/part-editor/PartStudio.cmd` hoặc `& .\tools\part-editor\run.ps1` từ gốc repo. Script biên dịch hai lớp Java của editor bằng JDK và JAR sẵn có tại `Server/target/TeaMobi-1.0-RELEASE-jar-with-dependencies.jar`, hỏi IP/cổng game rồi mở URL `http://127.0.0.1:8182/?token=...`. Máy này đang có process Part Studio nghe cổng 8182 tại lúc bàn giao; kiểm tra process trước khi chạy phiên thứ hai.
- Đăng nhập tài khoản `is_admin=1` trong UI. Part Studio gửi action `-126` tới **game server**; BE đang chạy phải có action admin tương ứng. HTTP chỉ nghe loopback và dùng token phiên. Không ghi mật khẩu vào URL hoặc file.
- Các lệnh đọc/ghi SQL chạy trên game server, kết nối DB theo `server.properties` của BE; máy mở Part Studio không cần nối trực tiếp MariaDB. Nếu UI báo “Không có action này”, kiểm tra BE đã build/deploy/restart bản mới. `image-list` và việc xoá bộ đếm chờ đăng nhập sau xác thực admin cũng phụ thuộc BE đang chạy.
- Sau **Lưu vào SQL**, khởi động lại BE để nạp lại `part` và `item_template` trong RAM. Việc lưu tăng phiên bản data/item trong `admin_editor_state` để client tải lại cache, nhưng không thay được cache BE đang chạy.

## Mô hình dữ liệu cần giữ

| Item type | Chức năng | Nơi lưu ngoại hình |
| --- | --- | --- |
| 5 | Cải trang | `cai_trang` trỏ `head`, `body`, `leg`, `bag` |
| 18 / 21 | MiniPet có part | `mini_pet` trỏ đủ `head`, `body`, `leg` |
| 72 | Pet đi theo | `pet_follow` chứa sprite Image ID, kích thước một frame và số frame; hoặc dùng icon item làm ảnh tĩnh |

Các ô body là vị trí trang bị, còn `type` là loại item; đừng dùng số ô body làm type. Pet type 72 không dùng bộ part đầu/thân/chân. Type 18 cũ chỉ dùng được theo luồng `mini_pet` khi có đủ ba part; ảnh `pet_follow` cũ không thay cho mapping này.

**Lưu ý chuyển type:** `loadItem()` trong UI đổi item type 18 thành 21 khi mở để sửa; `PartEditorServer.save()` cũng đổi 18 thành 21 trước khi ghi. Do đó lưu lại một item 18 bằng editor sẽ chuyển thành 21. Đây là hành vi code hiện tại, cần đánh giá tác động trước khi thay đổi hoặc xử lý hàng loạt.

`part.DATA` là danh sách `[imageId, dx, dy]`: đầu type 0 có 3 frame, thân type 1 có 17 frame, chân type 2 có 14 frame. Unity chọn các frame đó qua 33 dáng `CharInfo`; 33 dáng không phải 33 ảnh phải tải. `dx/dy` là byte có dấu từ −128 đến 127. Part chỉ chứa ảnh và tọa độ, không chứa item nào dùng part đó; không gán bộ part vào pet chỉ vì ID liền kề.

## Luồng thao tác trong UI

1. Chọn **Cải trang**, **Tất cả pet**, **MiniPet · 21** hoặc **Pet đi theo · 72** trong kho. Tìm theo tên/ID, mở item hoặc tạo mới. Item đang có đọc trực tiếp từ SQL. Mở catalog/tải lại trang trong cùng phiên editor giữ phiên admin; đóng editor rồi chạy lại phải đăng nhập lại.
2. Với cải trang/MiniPet, nạp part BE hoặc part Server 14 theo ID; **Nạp nhiều part** nhận 2–3 ID, tự xếp đầu/thân/chân sau khi kiểm tra đủ. Ảnh Server 14 được so với ảnh BE ở zoom x1–x4; nếu ID trùng nhưng nội dung khác, hệ thống cấp Image ID mới. Part nguồn ở `Server/resources/reference/server14/part.bin`; ảnh nguồn cần ở `../NRO-server15-assets/image/zoomN/icon/` so với repo.
3. Chọn mức zoom của PNG nguồn trước khi nhập. Có thể tải PNG từng frame, chọn nhiều PNG từ máy (sắp theo số trong tên), hoặc chọn ảnh đã có trên server qua modal tìm/lọc khoảng Image ID. Chọn nhiều lần sẽ đi tiếp từ frame trống hoặc từ vị trí chỉ định. UI báo lỗi nếu số ảnh vượt phần còn lại. Ảnh part phải có đủ mức zoom theo kiểm tra của BE trước khi gán/lưu.
4. Xem preview 33 dáng, kéo hoặc dịch 1px để căn `dx/dy`, chọn trực tiếp hình đầu/thân/chân trong preview. MiniPet có nhóm 11 dáng thường dùng; chân MiniPet thường xếp 00 bay, 01 đứng, 02–06 chạy, 07 nhảy, 08 rơi. Các frame còn lại vẫn thuộc cấu trúc part 3/17/14. Preview MiniPet không vẽ part đầu ở dáng 07, 08, 12, 23 vì ảnh chân đã có đầu. **Hiện part mẫu cho frame trống** chỉ hỗ trợ căn chỉnh, không ghi part mẫu vào SQL.
5. Với type 72, chọn icon item hoặc sprite `pet_follow`: một PNG gồm các frame xếp dọc, nhập rộng/cao một frame theo x1 và 1–127 frame. Preview sprite riêng ở khu vực **Hình pet đi theo**. Không nhập part đầu/thân/chân cho type này.
6. **Lưu vào SQL** kiểm tra type, part, số frame, Image ID/PNG, giới hạn số, revision để tránh ghi đè thay đổi mới, rồi ghi trong transaction. Part đang dùng mà thay đổi ảnh/tọa độ được cấp Part ID mới; part cũ và item khác giữ nguyên. **Xóa mapping** bỏ ngoại hình nhưng giữ item. **Xóa item cuối** chỉ áp dụng khi đó là ID cuối và không còn tham chiếu được kiểm tra.

## Ảnh, ID và nguồn Server 14

- Image ID là ID ảnh dùng trong từng frame; Part ID là ID hàng `part`, và `item_template.part` là một trường riêng. Cải trang chỉ thay đầu có thể đặt `item_template.part` bằng Part ID đầu; bộ đủ ba part thường để `-1` và dùng mapping trong `cai_trang`/`mini_pet`.
- Part Server 14 có 2.097 bản ghi tham chiếu. `admin_part_alias` ghi quan hệ part nguồn ↔ part BE khi sao chép part trùng; thao tác cấp ID không tự gắn part vào item.
- Ảnh vừa upload chỉ ở trạng thái chờ; **Lưu vào SQL** mới ghi ảnh lên server. Chọn đúng zoom nguồn, đặc biệt PNG lấy từ `resources/normal/image/4/icon` phải chọn x4. Nếu thiếu PNG, UI đánh dấu Image ID; chọn lại ảnh server hoặc tải ảnh trước khi lưu.
- Các script đồng bộ/audit Server 14 nằm trong `tools/part-editor/`; chạy từ gốc repo theo README. Chúng là công việc nhập và đối chiếu dữ liệu riêng, không phải bước bắt buộc mỗi khi sửa một item.

## Kiểm tra trước khi tiếp tục

1. Xem `git status` và `tools/part-editor/README.md`; kiểm tra process cổng 8182 để tái dùng phiên editor hiện có thay vì mở trùng.
2. Nếu sửa UI, kiểm tra cú pháp JavaScript trong `<script>` của `index.html` và thao tác preview bằng một item hiện có. Nếu sửa action/SQL, build BE và xác nhận bản deploy đang chạy hỗ trợ action mới trước khi thử ghi thật.
3. Khi kiểm chứng lưu, chọn item thử phù hợp hoặc môi trường dữ liệu cô lập; đọc lại item từ SQL và restart BE rồi thử trong Unity. Chưa có kiểm thử ghi DB hoặc preview trực tiếp mới nào được thực hiện trong lượt viết handoff này.
