# Bàn giao dự án NRO — 27/11/2026

## 1. Mục tiêu và phạm vi hiện tại

Tiếp tục hoàn thiện **Bot Manager** trong `bot-manager/` để các bot kiểm thử server tự đăng nhập, làm nhiệm vụ, di chuyển, đánh/nhặt quái, hồi phục và mua vật phẩm ở làng. Vấn đề gần nhất: bot tới **Bò Mộng (NPC 17)** ở nhiệm vụ Thần Mèo `[9]` nhưng cứ mở NPC mỗi 5 giây, nhiệm vụ không tăng bước. Một thay đổi server đã được viết để xử lý lỗi này, **chưa commit, chưa deploy và chưa kiểm chứng trực tiếp trên server**.

## 2. Trạng thái Git và phần đã hoàn thành

- Repo: `D:\Code\game nro\Folder Server`, nhánh `main`, remote `origin` là `thanhbui27/Ngoc-Rong-For-Study`. Tại lúc bàn giao, `HEAD` và `origin/main` cùng ở `d716354b7` (`Improve bot quest navigation and village supplies`), đã push.
- Commit này có các sửa đã hoàn thành: nhiệm vụ 9 đi map 47 gặp Bò Mộng, chờ Tàu Pảy Pảy, lên Tháp Karin map 46 gặp Thần Mèo; server cho gọi Tàu Pảy Pảy từ bước 9.1; nhận diện mục tiêu quái nhiệm vụ, chọn map gần/vừa sức, tránh tuyến bị server từ chối; nhiệm vụ giải cứu về hành tinh gốc khi tàu bị khóa; tìm NPC báo cáo/bái sư đúng map; ăn đậu hồi HP/KI, mua và ăn Nho xanh ID 212 khi hết thể lực; tự mặc đồ trong túi và mua bộ trang bị cơ bản đúng hệ khi ghé làng. Bot có UI quản lý, tạo/chạy/dừng hàng loạt, lưu cấu hình, reconnect và log.
- Trước thay đổi server mới nhất, bộ Python `python -m unittest discover -s tests -q` đạt **26/26**, và `node --check app.js` đạt. Không có kết quả kiểm thử trực tiếp toàn bộ nhiệm vụ 9 trên server đang chạy.

## 3. Thay đổi code **chưa commit** liên quan công việc này

- `Server/src/main/java/nro/models/npc/NpcFactory.java`: trong `BO_MONG.openBaseMenu()`, gọi `TaskService.gI().checkDoneTaskTalkNpc(player, this)` sau `canOpenNpc()`, rồi `return` nếu nhiệm vụ hoàn thành. Trước đó NPC luôn trả menu nhiệm vụ hằng ngày; vì thế bot mở NPC 17 lặp lại nhưng bước 9.0 không hoàn thành. `TaskService.java` đã có `doneTask(TASK_9_0)` và `doneTask(TASK_10_2)` cho Bò Mộng, không cần sửa luật nhiệm vụ ở file đó.
- `bot-manager/routes.py`: đọc tên option từ bảng `item_option_template` trong `ngocrong-clean.sql`.
- `bot-manager/bot.py`: `_named_items()` thêm `label` cho mỗi option, thay dấu `#` bằng giá trị; option có tên trống giữ label trống; option không biết tên vẫn hiển thị ID.
- `bot-manager/app.js`: túi/rương/đồ đang mặc hiển thị `label`, lọc nhãn trống. Ví dụ quần ID 6: `HP+33 · Set Gohan · (5 món +300% may mắn, +50% vàng rơi từ quái) · Không thể giao dịch`, thay cho các mã 6/263/264/30/73.
- `bot-manager/tests/test_bot.py`: kiểm tra cách đặt tên option. Các file trên đều đang ở trạng thái `M`, chưa commit/push.
- `bot-manager/bot-run.cmd` đang untracked; chưa xác nhận nội dung và chưa đưa vào commit.

**Thay đổi khác trong working tree:** có sửa/xóa/di chuyển nhiều file Part Studio, clone server, ảnh/audit và `.gitignore`. Chúng nằm ngoài phần bot/nhiệm vụ đang bàn giao. Không tự ý `git add .`, khôi phục hay xóa chúng; kiểm tra `git status` và chỉ stage file đúng phạm vi nếu người dùng yêu cầu push.

## 4. Quyết định kỹ thuật/nghiệp vụ cần giữ

- Bot là client Python dùng socket theo giao thức server, UI chỉ bind `127.0.0.1:8765`; code ở trong `Folder Server` để deploy cùng repo. Tối đa 50 bot/app, bot đã lưu không tự chạy khi khởi động Bot Manager.
- Bot phải đọc tiến độ nhiệm vụ từ gói server, không tự tăng bước. Các nhiệm vụ đặc biệt cần luật cụ thể; không cho farm ngẫu nhiên khi bước tìm kiếm chưa có luật. Log phải nêu rõ trạng thái chưa hỗ trợ hoặc không có tuyến.
- Nhiệm vụ 9.0 cần **nói chuyện** với NPC 17 tại map 47; NPC này phải gọi `checkDoneTaskTalkNpc` trước menu hằng ngày. Ở bước 9.1, Tàu Pảy Pảy phải xuất hiện; bước 9.2 đi map 46; bước 9.3 nói với NPC 18. Server đã commit điều kiện `getIdTask(player) >= TASK_9_1` trong `Service.callTau77()`.
- Đậu thần hồi HP/KI lấy từ túi/cây ở nhà; Nho xanh ID 212 hồi 20% thể lực, bán 1000 vàng ở shop làng của ba hệ. Server chỉ cho ăn nho khi thể lực không quá 50%. Bot chỉ nhặt item trên map thuộc mình hoặc không có chủ, và ưu tiên item nhiệm vụ.
- Route planner dựa vào waypoint từ `ngocrong-clean.sql` và tàu giữa map 24/25/26. Cổng/tàu bị từ chối cần tạm chặn để tìm đường khác; map riêng hoặc yêu cầu nhiệm vụ không được giả định luôn đi được.
- Tránh cài/thêm Docker engine hoặc stack mới; tuân thủ hướng dẫn Docker do người dùng cung cấp. Bot Manager chạy được bằng Python, không cần Docker.

## 5. Vấn đề còn tồn tại

- Lỗi vòng lặp NPC Bò Mộng mới được sửa ở source server, **chưa build/deploy/restart server**, nên bot trên server hiện tại có thể vẫn kẹt. Lần thử `mvn -q -DskipTests compile` không chạy được vì máy không nhận lệnh `mvn`; chưa xác nhận build Java.
- Nhiệm vụ đặc biệt, boss, tìm kiếm về sau chưa có luật tự động đầy đủ. Nếu không rõ luật, bot hiển thị bước chưa hỗ trợ; không coi 26 bài unit test là bằng chứng đã chơi hết tuyến nhiệm vụ.
- Tên option vật phẩm lấy từ seed SQL trong repo. Nếu DB production có option mới/chỉnh tên, cần đồng bộ seed hoặc nguồn metadata; option không biết tên sẽ còn hiển thị ID.
- `bot-manager/README.md` có thể chưa phản ánh đầy đủ hành vi tự mua trang bị cơ bản đã commit; cần rà lại khi cập nhật tài liệu.

## 6. Task đang dở và bước tiếp theo

1. Xác nhận phần sửa `NpcFactory.java` phù hợp luồng nhiệm vụ 9/10; build Java bằng công cụ Maven sẵn có trên môi trường deploy hoặc cấu hình Maven hiện tại, không dựng Docker chỉ để build.
2. Deploy/restart **server** và restart Bot Manager nếu có thay đổi Python; thử bot đang ở nhiệm vụ 9.0: tới map 47, mở NPC 17 **một lần**, nhận gói nhiệm vụ sang bước 9.1, boss xuất hiện, rồi hoàn thành tuyến tới NPC 18. Ghi lại log nếu không tăng bước.
3. Kiểm tra UI túi/rương/đồ đang mặc hiện tên option sau khi restart Bot Manager và tải lại trang.
4. Nếu người dùng yêu cầu push, stage có chọn lọc các file liên quan; không gom các thay đổi Part Studio/clone server chưa rõ chủ sở hữu.

## 7. Lưu ý tránh sửa sai

- Với nhiệm vụ 9, lỗi hiện tại nằm ở **server NPC**, không phải việc bot thiếu lệnh chọn menu: menu Bò Mộng là menu nhiệm vụ hằng ngày, chọn nó không hoàn thành bước 9.0.
- `Server/src/main/java/nro/services/TaskService.java` đã ánh xạ NPC 17 với `TASK_9_0` và `TASK_10_2`. Giữ thứ tự kiểm tra nhiệm vụ trước menu thường trong `NpcFactory`.
- Các con số `option.id` là ID template; nhãn chính xác phải lấy từ `item_option_template`. Option tên trống như ID 73 nên ẩn, không đoán ý nghĩa từ `param`.
- Đừng kết luận server đã cập nhật chỉ vì Git đã push: sửa `NpcFactory.java` hiện chưa nằm trong commit `d716354b7` và binary server đang chạy có thể là bản cũ.
