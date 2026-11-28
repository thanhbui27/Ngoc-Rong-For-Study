# Clone dữ liệu client từ server NRO

## Giao diện web cục bộ

Trên Windows, bấm đúp `CloneStudio.cmd` ở thư mục gốc repo hoặc `tools/clone-server/run.cmd`. Cửa sổ lệnh giữ UI hoạt động; đóng cửa sổ để tắt UI.

Từ thư mục `Folder Server`, chạy:

```bash
bash tools/clone-server/run.sh --ui
```

Trang tự mở tại `http://127.0.0.1:8183/`. Bấm **Chọn thư mục…** để chọn nơi lưu bằng hộp thoại hệ thống (hoặc gõ đường dẫn), chọn server, zoom, phạm vi ảnh rồi bấm **Bắt đầu clone**. Trang hiển thị log, số lượng đã lấy, file JSON để tải và các ID còn thiếu. **Mở bản lưu** đọc lại kết quả trong thư mục đã chọn. Bấm **Dừng** để ngắt lượt clone; chạy lại cùng thư mục sẽ tiếp tục ảnh/map đã có. UI chỉ nghe trên `127.0.0.1` và dùng Python chuẩn, không cần cài thêm package. Dùng `--ui --port 8184` nếu cổng 8183 bận.

Chọn thư mục đã có `report.json` sẽ mở ngay preview Part mà không kết nối lại server; UI nhớ thư mục này để mở lại ở lần chạy sau. Bấm **Tải tiếp / cập nhật** nếu muốn làm mới dữ liệu trong thư mục cũ. Chọn thư mục mới chưa có `report.json` rồi bấm **Bắt đầu clone** để tải từ đầu vào thư mục đó. Khi đổi thư mục, UI xóa cache part/ảnh của dự án trước.

Sau khi clone hoặc **Mở bản lưu**, các tab riêng cho phép:

- **Part + hình:** tìm part theo ID/loại, xem mọi frame cùng Image ID, `dx/dy` và PNG. Có thể duyệt các bộ ba part liền kề loại đầu/thân/chân hoặc nhập ba ID để ráp theo bảng dáng `CharInfo` của Unity. Bộ liền kề chỉ là gợi ý để duyệt; dữ liệu part không ghi item nào sở hữu bộ đó. Nếu thiếu PNG, tab báo rõ ID thiếu và chỉ dùng mức zoom khác khi có ảnh.
- **Item · Cải trang · Pet:** lọc cải trang type 5, mini pet type 18/21, pet đi theo type 72 hoặc xem mọi item. Xem icon, `part_id` từ server và các part đã có mapping; chọn đầu/thân/chân để ráp preview. Chọn hành động **Đứng** hoặc **Chạy** rồi bấm **Phát**. Preview dùng quy tắc frame trong Unity `Char.updateCharStand` và `Char.updateCharRun` với nhịp `FixedUpdate` 20 ms ở tốc độ 1×; các dáng khác vẫn chọn thủ công. Mini pet được vẽ theo thứ tự lớp trong `Char.paintCharBody`. **Dừng** hoặc đổi item sẽ ngắt phát. Mapping tự lưu nằm trong `mappings/costume-parts.json` hoặc `mappings/mini-pet-parts.json` của bản clone. Tab không ghi vào DB/game server. Type 72 dùng `pet_follow` và sprite riêng nên chỉ hiện icon item khi bản clone không chứa sprite đó.
  Sau mỗi lượt clone, tool tự gắn part từ các mapping đã xác nhận của bản clone tham chiếu khi item khớp tên/loại/giới tính/icon và từng part khớp toàn bộ frame; ID part có thể khác. Nếu icon đổi, tool chỉ đối chiếu theo tên khi bộ ba part có đủ frame trùng khớp và không bị trùng tên với bộ khác. Tool cũng dùng `part_id` của item type 5 để gắn đầu khi hợp lệ, và vẫn đối chiếu SQL seed cục bộ. Nó không đoán thân/chân chỉ vì ID nằm cạnh đầu. Mapping đã lưu thủ công được giữ nguyên. Mở một bản clone cũ trong UI cũng chạy bước tự gắn này. Kết quả từng lượt clone nằm ở `report.json` mục `auto_linked_parts`; item chưa đủ bằng chứng vẫn để người dùng chọn trong preview.
  Tab còn đối chiếu `ngocrong-clean.sql` cục bộ: cải trang phải trùng ID/type/tên/icon/`part_id` và toàn bộ frame part; mini pet phải trùng tên/giới tính và toàn bộ frame của cả ba part. Đây là **SQL seed trong repo**, không phải SQL tải từ server nhập vào. Bản Server 14 đang có 282 mapping cải trang (207 bộ đủ ba part) và 19 bộ mini pet đạt điều kiện. Mapping tự lưu được ưu tiên. Cải trang chỉ thay đầu được ráp với part thân/chân nền #1/#2 để xem nhân vật; phần nền không được lưu. Item chưa có mapping sẽ hiện icon và ghi rõ nguồn ảnh.
- **Map:** tìm map theo tên/ID và xem lưới tile ID từ packet map. Màu trong preview giúp phân biệt tile; không phải texture map thật của game.

## Dòng lệnh

Chạy từ thư mục `Folder Server` (Python 3.10+):

```powershell
python tools/clone-server/clone_server.py --server dragon14.teamobi.com:18001
```

Hoặc dùng Git Bash/WSL/Linux từ bất kỳ thư mục nào:

```bash
bash "D:/Code/game nro/Folder Server/tools/clone-server/run.sh" --server dragon14.teamobi.com:18001
```

Khi đang ở thư mục `Folder Server`, chỉ cần `bash tools/clone-server/run.sh --server HOST:PORT`. Bỏ `--server` để nhập địa chỉ khi chạy.

Nếu bỏ `--server`, tool hỏi địa chỉ `HOST:PORT`. Mặc định tool thử cả zoom 1, 2, 3, 4 và lưu ngoài Git tại `../NRO-clones/HOST-PORT`. Có thể chọn thư mục bằng `--out D:\captures\server14`.

Tool gửi các yêu cầu đọc như client: gói `-87` chứa `dart/arrow/effect/image/part/skill`; gói cập nhật `-28` cho map, skill và item; các tile map riêng; luồng ảnh resource `-74`; và ảnh nhỏ `-67`. File gốc nằm trong `raw/`, `game-data/`, `resources/`, `icons/`. JSON đã giải mã nằm trong `decoded/`. `report.json` ghi số lượng, phiên bản, lỗi và phần thiếu. Chạy lại cùng `--out` sẽ giữ ảnh và tile map đã tải, đồng thời cập nhật các gói và resource nếu server đổi.

Ví dụ chạy ngắn để kiểm tra kết nối:

```powershell
python tools/clone-server/clone_server.py --server dragon14.teamobi.com:18001 --zooms 1 --max-files 2 --max-icons 5 --skip-maps
```

Đọc lại 6 file `.bin` đã có mà không kết nối server:

```powershell
python tools/clone-server/decode_game_data.py D:\captures\server14\game-data --out D:\captures\server14\decoded
```

`part.json` chứa ID part, type và từng frame `[image_id, dx, dy]`; `image.json` chứa vị trí vùng ảnh trong atlas; `dart.json` chứa các dãy frame đầu/đuôi; các file còn lại có cấu trúc tương ứng. Dữ liệu chưa biết định dạng được giữ nguyên ở `raw/` thay vì đoán nội dung. Gói item type 101 là phần mở rộng chưa có bộ đọc.

Nếu server không gửi danh sách phiên bản ảnh nhỏ cho phiên ẩn danh, tool lấy các ID được tham chiếu trong game-data và item template. Để quét thêm một dải ID cụ thể:

```powershell
python tools/clone-server/clone_server.py --server dragon14.teamobi.com:18001 --zooms 1 --image-range 0:12000
```

`--icons referenced` chỉ tải ID đã biết; `--icons none` bỏ ảnh nhỏ. Một số server công bố số file resource lớn hơn số thực sự gửi; báo cáo sẽ đánh dấu `complete: false` dù luồng đã kết thúc. Tool chỉ lấy dữ liệu mà server cung cấp qua giao thức client ẩn danh. Các bảng SQL nội bộ như `mini_pet`, `pet_follow` và dữ liệu tài khoản cần nguồn riêng.

Map không phản hồi sẽ nằm trong `maps.missing`; tool mở phiên mới và tiếp tục ID kế tiếp. Với Server 14 đã kiểm tra, ID 169 không phản hồi còn 170–186 trả dữ liệu.
