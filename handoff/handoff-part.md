## Cập nhật 28/11 — sửa item hiển thị khác khi dùng

Deploy code `ab387c953` thành công qua Actions run `46133840196` lúc 17:13 ngày 28/11, dùng input không backup Docker (DB đã áp dụng đủ V29). Đã đối chiếu toàn bộ 2.686 part từ server đang chạy với DB, 12 mẫu PNG x1/x4 khớp file local. Unity đã làm sạch cache và tải lại part version 30, đăng nhập `bot79` vào đảo Kame (map 5).

- DB live qua tunnel DBeaver đã áp dụng V26–V29: `mini_pet` 49 → 119 hàng (118 đúng type, 1 hàng cũ type 0 không được loader sử dụng), `part` 2539 → 2686; `cai_trang` 1007 → 1012. Thêm 70 mapping, sửa 5 pet cũ 1224/1225/1226/1243/1244 bị đụng ID part. Không đổi tên/icon/type item, part cũ hoặc 12 mapping pet đã tùy chỉnh hành động.
- Kiểm tra thật sau deploy: acc test tại Kame nhận/mặc item 1317, preview `[553,551,2156]`, mặc và đóng preview vẫn đúng ba part này. Túi ban đầu đầy nên đã cất món test 421 vào rương; Kimono 1174 chuyển vào túi khi mặc Rosé. Kết quả tại `tools/client-patches/verification.json`. Unity hiện để Play ở Kame. Script test một lần `NroHihi/Assets/Editor/VisualAccountSmoke.cs` đã ngừng callback sau khi pass, không chứa thông tin đăng nhập; có thể xóa script khi dừng Play lần tới.
- V29 sửa 8 cải trang 1317/1731/2040/2041/2064/2098/2124/2608 sau khi đối chiếu icon với PNG đầu/thân/chân. Không lấy ID ảnh gần nhau làm bằng chứng cùng nhân vật. Các bộ 1272/2122/2123 giữ cách căn frame riêng; 2148 là Broly custom, icon dùng lại mẫu Broly khác nên cần icon đúng bộ để hoàn thiện.
- `CostumeAppearance` dùng chung quy tắc cho shop và nhân vật: chỉ type 5 dùng `cai_trang`, slot trống về đầu/áo/quần thật, kiểm tra đúng loại part. Quần đi biển 691–693 dùng part chân 700/702 thay vì bị đọc thành đầu. Item thiếu ngoại hình không được mặc nhưng vẫn chuyển rương → túi bình thường.
- `MiniPetManager` chỉ nạp item type 18/21 với đúng loại part và đủ PNG x1–x4. Pet 1322 thiếu Image 20831 cả bốn zoom nên chưa dùng được; không có nguồn ảnh thay thế.
- Unity ngoài repo đã sửa `NroHihi/Assets/Scripts/Char.cs` và `Controller.cs`: preview mới không giữ bộ trước và đóng panel khôi phục cả bag=-1. Patch và 5 kiểm tra tại `tools/client-patches/`; Unity đã biên dịch và pass cả 5.
- Audit tái lập: `ReadVisualDatabase.java` đọc qua tunnel có sẵn (không Docker); `audit_visual_identity.py` xuất `visual-identity-report.json`. Hiện 1052 ánh xạ khớp nguồn, 12 biến thể pet chủ đích, 0 sai slot, 0 mini pet thiếu mapping. Còn 21 cải trang chưa có mapping được xác minh và 1 Image ID thiếu nguồn; không tự đoán ảnh.
- Kiểm thử SQL V26/V27/V28/V29 trên bảng TEMP hai lần, không ghi bảng thật trong bước thử; đối chiếu sau apply giữ toàn bộ part cũ và các bảng item/flag/ảnh tên; V29 chỉ sửa đúng 8 mapping cải trang đã xác minh.
- Deploy có lựa chọn `--skip-database-backup` cho DB đã backup và áp dụng đủ migration; lựa chọn này không gọi Docker và từ chối deploy nếu còn migration pending. Actions manual input `skip_database_backup=true`; push thông thường vẫn giữ backup như cũ.

# Bàn giao Part Studio — cập nhật 28/11/2026

## Cập nhật từ luồng Clone Studio

### Sửa dữ liệu BE thiếu — 28/11/2026

- Đã audit file BE thực tế và `ngocrong-clean.sql` bằng `tools/part-editor/audit_be_assets.py`. Dùng bộ đọc SQL `tools/clone-server/sql_seed.py` để giữ đúng escape MySQL (`\r\n` trong JSON DATA là khoảng trắng, không phải part hỏng). Report gọn tại `tools/part-editor/be-asset-repair-report.json`; đây không phải kết quả đọc DB đang chạy.
- `EffectAssetResolver` được nối vào `Resources.effData`: chọn frame data theo đa số nghiêm ngặt (ít nhất 2 nguồn), giữ bộ được yêu cầu nếu không đủ bằng chứng. Khi thiếu atlas của một zoom, chỉ dùng atlas cùng Effect ID có data byte-identical rồi nhân pixel bằng nearest-neighbor ở runtime. Không đổi sang effect khác hoặc ghi lại PNG gốc. Probe trên tài nguyên thật sửa được 13 cặp ID/zoom: 8 cặp thiếu atlas và 5 bộ x2 có data lệch. Effect #72/#73/#1000 chưa có atlas khớp để khôi phục.
- V25 `repair_stale_visual_mappings`: xóa có điều kiện 6 mapping cải trang cũ đang trỏ vào sách/hộp quà/item trống; giữ mapping khi item hiện là type 5 hoặc part đã được sửa. Xóa pet_follow/mini_pet cũ chỉ khi item đã được V24 nhận diện thành cải trang đúng tên/icon nguồn. Dragon #2097 có ảnh thật 17×10 ở x1, được sửa khai báo thành 1 frame tĩnh thay vì 75×75×8. Migration không sửa NAME của item.
- Không tìm thấy nguồn ảnh thiếu của mini pet #1322 (Image ID 20831), 10 bộ cờ, 18 tên sprite, 3 quái #28/#29/#30 và nhiều pet/custom costume trong các thư mục `D:\Code\game nro` hoặc lịch sử Git đã kiểm tra. Người dùng xác nhận không có bộ resource gốc khác. Không nhân bản nhân vật/ảnh khác ID để lấp chỗ trống; các bộ này vẫn còn thiếu nguồn.
- V25 **chưa áp dụng DB thật**: cấu hình hiện trỏ localhost:3306/ngocrong nhưng cổng không mở. Không dùng Docker. BE cần build/restart để dùng resolver mới, và chạy migration trên DB đích để nhận thay đổi SQL. V23/V24 cũng chưa được agent chạy trong phiên.
- Đã compile `Resources.java` cùng resolver bằng JDK với JAR dependency sẵn có. Test JUnit cho resolver và V25 chạy trên H2 in-memory (không dùng Docker/dữ liệu thật); kiểm tra byte/zoom, không lấy nhầm atlas, bảo vệ mapping tùy chỉnh và chạy SQL lặp lại. Test parser kiểm tra escape MySQL và JSON.

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


## 2026-11-28 — V30, remaining wearable visuals

- User explicitly chose: costumes with only an avatar and no model stay blocked;
  do not synthesize head-only costumes. Fourteen IDs remain blocked; see
  `tools/part-editor/visual-equipment-audit.json` for the exact lists.
- Recovered 7 Cumber costume links from `BossData.CUMBER/CUMBER2` (full parts
  1387/1388/1389 and 1390/1388/1389). Fixed the two missing Cumber item icons.
- Mini pet 1322 now uses copy-on-write body 2686. Missing pose 20831 repeats its
  own pose 20830; unsupported poses use its own neutral frame instead of human
  image 34. This is a degraded same-pet animation, not a recovered original frame.
- Broly 2148 icon 32602 comes from his own head 18591. Missing icons for 1315/1316
  come from their currently configured model parts (32613/32614); names unchanged.
- Mounts resolve `30000 + template.part` for types 23/24. Six missing mount sets
  use their own object icon as a static front; mount 66 keeps its animated front.
- Repaired back-accessory part collisions; preserved matching original animations,
  allocated 27 static same-item flags 110–136, and blocked 7 unrecoverable entries.
  Effect accessories 201/205/207 use their native effects. No name-based fallback.
- Titles write exactly one effect ID (12-byte add, 7-byte targeted remove). Apply `tools/client-patches/wearable-titles.patch`
  to other Unity checkouts. Ten titles have icons taken from their own effect art;
  title 1308 stays blocked because it incorrectly referenced Halloween (87).
- Type-72 followers require valid, explicitly configured sprites at every zoom.
  Twelve unavailable/wrong pets stay blocked, including 2097 (blue arm image collision).
  Working full animated followers: 2105, 2107, 2116, 2118.
- Auras 1/10 get transparent missing layers while keeping their existing artwork.
  Entirely missing aura sets 11/12 are suppressed; there is no substitute effect.
- SQL V30 applied through the existing DBeaver tunnel, with no Docker. Read-only
  visual backups and rehearsal exports are under `%TEMP%/nro-remaining-visuals`.
  Both rehearsal runs produced identical catalog contents. Data/item versions 31/29.
- Reproduce inspection with `audit_visual_equipment.py --snapshot EXPORT --output REPORT`;
  `repair_remaining_visuals.py` documents the source-to-output asset derivation and
  requires the pre-V30 export. The JSON repair manifest lists only task-related assets.

- Follow-up: `Controller2` already parses -128 through `sbyte.MinValue`. The primary
  controller now skips rereading it. Title removal uses action 1 + its effect ID,
  preserving other effects; bag updates remove only the previous bag effect instead
  of clearing the whole 201–254 range (which also contains title IDs 214/215/217/218).
  Removed the redundant title emission in UseItem after a rejected equipment change.

- Follow-up for rương: retain the removed title's effect ID before clearing its body
  slot; refresh map appearances and flag bags after body→box moves. This keeps
  boxed titles, mounts and back accessories from remaining visible to observers.


### Final deployed verification (18:53, 2026-11-28)

- Pushed/deployed source through `063dcda07`; successful no-Docker workflow run
  `46141188953`. The following documentation-only commit records the evidence.
- Cleared RMS cache with a sibling backup and downloaded it again. Account is
  logged in at Thần Mèo admin, đảo Kame; restored its equipment after the tests.
  The user changed costume/mount/mini-pet while testing; those newer choices were
  preserved in the final run. Test purchases are retained in the character's rương.
- Native gameplay checks passed: 1256 Cumber full outfit; 1322 werewolf mini-pet;
  1021 Mjolnir flag 69; 1131 mount 30012 including both downloaded layers;
  1293 title effect 88, including immediate removal on body→box and restoration;
  1161 back flag 128 with its correct own-image response (unsigned flag request).
- Two native packet regression checks passed: targeted title removal retains the
  bag effect; bag updates retain a title whose effect ID lies in 201–254.
- All three model-derived inventory portraits (32602/32613/32614) downloaded from
  the deployed server match the pushed PNG bytes exactly. The final catalog audit
  has zero missing inventory icons among ready visuals and no wrong-slot mappings.
- Evidence: `tools/client-patches/visual-equipment-verification.json`. The local
  one-use Unity editor helper has unsubscribed itself; its login request file was
  deleted immediately after use. Temporary DB credential copy was removed.
