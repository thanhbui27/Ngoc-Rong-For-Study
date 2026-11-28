# Bàn giao Clone Studio — 28/11/2026

## Cập nhật mở rộng animation sau a951a32e5

- Đã thêm tab **Effect · NPC · Quái · Skill**, bộ đọc `extended_data.py`, catalog `extended_studio.py`, renderer `extended.js`, capture `capture_extra.py` và importer `import_assets.py`. Các phần mô tả giới hạn cũ bên dưới cần đọc cùng cập nhật này.
- Giải mã trọn packet `sub6`: bản clone hiện có 88 NPC với part/menu và 100 mẫu quái. NPC chạy Đứng/Chạy theo CharInfo. Có preview 193 effect thường (22 bản ghi trống), 157 skill paint, 67 dart, 1 arrow. Skill dùng chỉ số mảng effectId−1 / dartType / arrowId−1 giống Unity; preview không mô phỏng chiến đấu và đường bay tới mục tiêu.
- Áo/quần có part được ráp lên nhân vật. Effect, sprite, cờ, sprite sheet pet có thể gắn bằng lớp vào item, chỉnh dx/dy và trước/sau nhân vật, lưu `mappings/item-visuals.json` (tối đa 8 lớp). Các liên kết không có trong packet vẫn phải xác nhận thủ công. Mount có part dùng tên `mount_<part>_0/1`; legacy chưa có part dùng lựa chọn sprite rõ ràng.
- Map hỗ trợ texture thật từ 128 lựa chọn tileset của bản clone; hỗ trợ file strip và `ID$tile.png`. Lựa chọn lưu ở `mappings/map-tilesets.json`; packet tile không chỉ ra tileset. Đã kiểm tra map 0 với `resources/zoom4/x4/t/1`: 0 ô thiếu texture. Chưa dựng nền và nước động từ dữ liệu phiên vào map.
- Capture mặc định thêm effect `-66`, quái `11`, cờ `-62/-63`, ảnh có tên `66`. CLI có `--extra-only`, `--skip-extra`, `--effect-range`, `--sprite-names`; UI có tải bổ sung và cùng tùy chọn. Batch 24, timeout hữu hạn, lưu raw trước khi decode, giữ ID thiếu/lỗi trong `report.extra_assets`, bỏ qua asset đã có đủ JSON/PNG. Kết nối bổ sung không cần chờ thông báo phiên bản resource. Không login hoặc dùng Docker.
- Đã thử tải bổ sung x4 từ Server 14: không lấy được asset nào trong các nhóm động, report ghi timeout. Probe riêng nhận handshake, `-111/-74/-29` nhưng không nhận phản hồi effect/quái/sprite đã thử. Đây là giới hạn quan sát của phiên hiện tại, không kết luận server vĩnh viễn không hỗ trợ.
- Đã nhập nguồn BE cục bộ `Server/resources/normal` vào bản clone ngoài Git để có dữ liệu xem: x4 hiện có 62 effect atlas, 79 quái, 102 bộ cờ, 95 sprite có tên và 5 pet sheet. Tổng 343 bản ghi nguồn riêng; nhãn source được giữ trong JSON/UI. Pet tham chiếu #2097 có PNG 68×40 không khớp khai báo 75×75×8 ở x1, preview báo sai kích thước; bốn pet sheet còn lại có PNG đúng cấu trúc. Không tự gắn dữ liệu tham chiếu này vào item Server 14.
- Kiểm tra: 13 unittest qua (renumber/mapping, template, atlas byte/short, packet flag/sprite, raw/resume capture, đường dẫn, tileset và nhập nguồn riêng); Python compile và JS syntax qua. Đã chạy trình duyệt Edge headless thật: NPC/effect/phát frame/áo quần, effect atlas/quái/cờ/aura từ nguồn riêng, map texture, lưu lớp effect rồi mở lại trên fixture tạm; không có lỗi JavaScript. Đã xem screenshot NPC, quái và map. Trình kiểm thử dùng playwright-core cài tạm, không thêm dependency cho sản phẩm.
- Bản clone và các asset nhập vẫn ngoài Git tại `D:\Code\game nro\clone test`. Muốn dùng trên máy khác cần capture hoặc nhập resource tương ứng; code không đóng gói toàn bộ PNG vào repo.

## Mục tiêu và trạng thái

Clone Studio tải dữ liệu mà client NRO ẩn danh nhận được từ một game server, lưu bản gốc và JSON đã giải mã, rồi cho duyệt part, ảnh, item, cải trang, pet và map trên UI cục bộ. Code ở `tools/clone-server/`, hướng dẫn sử dụng ở `tools/clone-server/README.md`. Launcher Windows ở `CloneStudio.cmd` và `tools/clone-server/run.cmd`.

Repo là `D:\Code\game nro\Folder Server`, nhánh `main`. Bản tự gắn part đã push lên `origin/main` tại commit `a951a32e5`; preview hành động theo Unity ở `38b28a3df`. Khởi động lại Clone Studio để nạp code mới. Working tree có nhiều ảnh và thay đổi ngoài phạm vi; dùng `git status --short -- <đường dẫn liên quan>`, không stage hoặc khôi phục hàng loạt.

## Chạy và mở bản clone

- Windows: bấm `CloneStudio.cmd`, hoặc từ gốc repo chạy `python tools/clone-server/ui.py --port 8183`. UI nghe trên `http://127.0.0.1:8183/`. Nếu cổng bận, dùng `--port 8184` sau khi kiểm tra process đang dùng cổng; không mở stack Docker mới.
- CLI: `python tools/clone-server/clone_server.py --server dragon14.teamobi.com:18001 --out "D:\Code\game nro\clone test"` (mặc định tải zoom 1–4). Các tuỳ chọn giới hạn lượt thử và chọn dải ảnh nằm trong README.
- Trong UI, **Mở bản lưu** trỏ đến thư mục có `report.json` để preview ngay, không tải lại. **Tải tiếp / cập nhật** mới kết nối lại server. Đổi thư mục sẽ xoá cache preview của dự án trước.
- Bản clone dùng để kiểm tra hiện nằm ở `D:\Code\game nro\clone test`, ngoài repo. Có `report.json`, 2.097 part, 2.112 item và 185 map có tile. Số liệu thuộc bản chụp này, không phải cam kết cho mọi server hoặc lần clone sau.

## Dữ liệu và luồng code

- `clone_server.py` điều phối socket, yêu cầu game data `-87`, update/map/item `-28`, resource `-74` và ảnh nhỏ `-67`; `nro_wire.py` xử lý giao thức. File thô nằm ở `raw/`, `game-data/`, `resources/`, ảnh ở `icons/zoom1` đến `zoom4`; kết quả ở `decoded/`, tiến độ và thiếu sót ở `report.json`.
- `decode_game_data.py` đọc các file nhị phân part/image/dart/arrow/effect/skill; `decode_item_packets.py` đọc item template. Mỗi frame part là `[image_id, dx, dy]`. **Part không chứa liên kết ngược đến item nào sử dụng nó.** Không suy ra mapping item từ ba ID part liền kề.
- `ui.py` phục vụ API và khởi chạy/dừng clone; `index.html` và `studio.js` là UI. `studio_data.py` cấp catalog, chi tiết part/item/map và kiểm tra mapping khi lưu. `char-poses.json` là bảng dáng lấy từ Unity `CharInfo`; preview ráp part theo bảng này.
- `reference_mappings.py` đối chiếu với `ngocrong-clean.sql` **cục bộ trong repo**, không phải SQL lấy từ server nhập. Mapping cải trang chỉ được đề xuất khi ID/type/giới tính/tên/icon/part ID của item và frame các part liên quan khớp. Mapping mini pet đối chiếu tên/giới tính và đủ frame của cả ba part. Mapping người dùng lưu trong bản clone được ưu tiên hơn nguồn tham chiếu.
- `auto_mapping.py` chạy sau khi CLI clone kết thúc và khi UI **Mở bản lưu**. `known-costume-parts.json` chứa 593 mapping tham chiếu (481 cải trang, 112 mini pet) từ bản clone đã gắn. Đối chiếu item theo loại/giới tính/tên/icon; dùng ID item để chọn bản ghi khi có nhiều ứng viên cùng thông tin. Khi icon đổi, chỉ nhận bộ đủ ba part không mơ hồ theo tên. Mỗi part phải khớp dấu vân tay của type và toàn bộ frame `[image_id, dx, dy]`; có thể tìm lại khi Part ID đổi. Nếu nhiều part có cùng dấu vân tay, dùng đầu từ `part_id` và độ dịch ID chung của bộ để phân giải; vẫn không rõ thì bỏ phần đó. Không so khớp nội dung PNG, nên Image ID hoặc frame đổi sẽ không khớp theo nguồn này.
- Thứ tự tự gắn: mapping tham chiếu đã xác nhận → SQL seed đã đối chiếu → đầu từ `part_id` hợp lệ của cải trang. Không tự suy thân/chân chỉ từ ID liền kề. Chỉ thêm item chưa có trong file mapping; giữ nguyên cả mapping đã lưu một phần. Số mapping thêm trong lượt CLI nằm ở `report.json.auto_linked_parts`. Mở bản lưu tự thêm mapping nhưng không cập nhật số này trong report. Thư mục có report của server khác bị CLI từ chối để tránh trộn dữ liệu.

## UI hiện có

- **Part + hình:** xem từng part, Image ID, `dx/dy`, PNG từng frame; duyệt bộ ba part liền kề đúng loại đầu/thân/chân; nhập ba ID và chọn dáng để ráp. Nhãn bộ liền kề nói rõ chưa biết item sở hữu.
- **Item · Cải trang · Pet:** lọc type 5 (cải trang), type 18/21 (mini pet), type 72 (pet đi theo) hoặc mọi item. Item có mapping được ráp đầu/thân/chân; thiếu mapping thì preview icon và báo rõ nguồn. Cải trang thiếu thân/chân có thể dùng part nền #1/#2 để xem, nhưng không lưu part nền vào mapping. Mapping chỉnh tay lưu ở `mappings/costume-parts.json` hoặc `mappings/mini-pet-parts.json` trong bản clone.
- Chọn **Đứng** hoặc **Chạy**, bấm **Phát** để chạy frame theo Unity `Char.updateCharStand` / `Char.updateCharRun`, nhịp 20 ms ở tốc độ 1×. Mini pet dùng thứ tự lớp của `Char.paintCharBody`; đổi item/tab sẽ dừng phát. Các dáng khác chọn thủ công.
- **Map:** duyệt map/tile ID; màu chỉ phân biệt tile, chưa phải texture map của game.

Ở bản Server 14 đã chụp: 487 item type 5, 112 mini pet type 18, không có item type 21 hoặc 72 trong catalog clone; tab mặc định hiện 599 item cải trang và pet, bộ lọc mọi item hiện 2.112 item. Có 591 bộ part liền kề để duyệt. SQL seed cục bộ đối chiếu được 282 mapping cải trang (207 bộ đủ ba part) và 19 bộ mini pet. Ví dụ pet item #892 có part #882/#883/#884 theo đối chiếu này. Đây là **mapping tham chiếu đã đối chiếu**, không phải kết quả SQL từ Server 14.

Bản clone hiện lưu 481 mapping cải trang: 480 có ít nhất một part, riêng #628 là `-1/-1/-1`. Sáu cải trang chưa có mapping là #1274/#1275/#1415/#1731/#1790/#1991; tổng cộng bảy item chỉ có icon. Có 382 mapping đủ đầu/thân/chân, 99 còn thiếu một phần hoặc trống. Cả 112 mini pet đã có mapping. Các file trong `D:\Code\game nro\clone test` nằm ngoài Git; bộ tham chiếu trong tool giúp tái tạo mapping khi mở bản clone khác.

## Kiểm tra đã chạy và giới hạn tự gắn

- `python -m unittest discover -s tools/clone-server -p test_auto_mapping.py -v`: 5 test qua, gồm ID part đổi, giữ mapping đã lưu, bộ trùng mơ hồ, icon đổi và yêu cầu đủ ba part khi icon đổi.
- Thử trên bản sao tạm chỉ có `decoded/items.json` và `decoded/part.json`: tự khôi phục 480 cải trang và 112 mini pet, mọi mapping khớp file đã lưu. Chạy lần hai thêm 0 mapping. Đây là kiểm tra hồi quy trên dữ liệu đã biết, chưa chứng minh mọi server mới đều gắn được.
- CLI và UI chạy được `--help`; đã kiểm tra cú pháp Python và diff. Chưa chạy một lượt capture mạng hoặc kiểm tra UI trực quan mới cho thay đổi tự gắn.
- Item/ảnh hoàn toàn mới, đổi Image ID hoặc đổi frame có thể cần chọn part trong preview. Mapping một phần đã lưu không tự bổ sung ở lượt sau; cần chỉnh tay nếu muốn hoàn thiện. Type 72 vẫn cần nguồn sprite riêng.

## Migration DB liên quan đã push

- `3579a3fd6`: V23 nhập/đối chiếu part tham chiếu và ghi mapping `cai_trang` cho dữ liệu Server 14.
- `3c9df80a8`: V24 upsert 487 cải trang vào `item_template` theo **ID nguồn**, ghi đè khi có ID và thêm khi chưa có theo yêu cầu người dùng; đồng thời ghi `cai_trang`. Đây là dữ liệu cố định của Server 14, không phải migration tự sinh cho server mới. V24 không dọn bản ghi `mini_pet`/`pet_follow` cũ khi ghi đè item trùng ID.
- Hai migration đã kiểm tra tĩnh nhưng **chưa thực thi trên DB đang chạy**. Chưa có MySQL Windows/listener/CLI khả dụng tại lần kiểm tra; cần xác định DB đích nếu người dùng yêu cầu áp dụng. Người dùng yêu cầu **không dùng Docker**; không khởi Docker để làm việc này. Không sửa phiên bản migration đã áp dụng, thêm phiên bản mới khi cần.
- Item nguồn #2062 Champa → part 2039/2040/2041; #2063 Belmod → 2042/2043/2044. PNG liên quan và icon tại zoom 1–4 đang là ảnh đen 1×1 ở nguồn/bản clone, nên mapping đúng ID vẫn không tạo preview có hình. Champa cũ #1907 có part 511/512/513 và ảnh thật.

## Giới hạn cần giữ đúng

- Client ẩn danh không đọc được các bảng DB riêng như `mini_pet` và `pet_follow`. Type 72 dùng sprite `pet_follow` riêng; bản clone hiện chỉ preview icon item nếu không có sprite đó. Không dùng mapping đầu/thân/chân của mini pet cho pet đi theo.
- Phần lớn item type 18 của bản clone có `part_id = -1`; không thể xác định đầy đủ part của chúng chỉ từ packet item. Không tự động lưu bộ part liền kề như mapping đã xác minh. Nếu người dùng gán thủ công, kiểm tra đúng loại part 0/1/2 và lưu riêng trong thư mục clone.
- `report.json` có thể ghi resource hoặc icon chưa hoàn tất dù luồng đã kết thúc; xem số ảnh thiếu theo từng zoom. Map không phản hồi cũng nằm trong `maps.missing`. Gói item type 101 chưa có bộ đọc đầy đủ.
- Preview nhân vật dựa trên dáng/anchor từ Unity; các hiệu ứng, sprite follow và texture map có luồng riêng. Đừng diễn giải canvas icon là preview chuyển động của pet.

## Nếu tiếp tục phát triển

1. Mở `tools/clone-server/README.md`, kiểm tra `git status` theo đường dẫn liên quan, rồi mở bản clone có `report.json`. Không cần tải lại dữ liệu để sửa UI/preview.
2. Khi thêm nguồn mapping mới, ghi rõ nguồn và điều kiện đối chiếu, giữ mapping tự lưu của người dùng ưu tiên cao nhất. Không ghi vào DB/game server từ Clone Studio.
3. Khi muốn preview pet đi theo type 72, trước hết xác định nguồn packet/sprite `pet_follow` thực sự có trong bản chụp hay không; nếu không có, cần nguồn dữ liệu riêng. Không tạo hình chuyển động từ icon item.
4. Sau sửa code, kiểm tra `python -m compileall -q tools/clone-server`, `node --check tools/clone-server/studio.js`, mở UI với bản clone có sẵn và kiểm tra API catalog/part/item. Chỉ chạy clone lại khi thay đổi giao thức hoặc cần dữ liệu mới.
