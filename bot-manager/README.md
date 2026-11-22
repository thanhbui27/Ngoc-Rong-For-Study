# NRO Bot Manager

Ứng dụng Python riêng để tạo và quan sát bot kiểm thử game server. Giao diện chỉ chạy trên `127.0.0.1`; mỗi bot kết nối với server bằng giao thức socket của client, không cần mở Unity hay Docker. Mã nằm trong `Folder Server` để đưa lên Git cùng server.

## Chạy

Yêu cầu Python 3.10 trở lên. Khởi động Login và Game server như hướng dẫn ở [`../README.md`](../README.md), rồi chạy:

```powershell
cd 'D:\Code\game nro\Folder Server\bot-manager'
python app.py
```

Trình duyệt sẽ mở `http://127.0.0.1:8765/`. Có thể dùng `python app.py --port 8766 --no-browser` nếu muốn chọn cổng hoặc không tự mở trình duyệt. Dừng bằng `Ctrl+C`; tất cả socket bot sẽ đóng.

Trong giao diện, nhập tên bot, tài khoản thử nghiệm, mật khẩu, địa chỉ và cổng game server, rồi bấm **Tạo và chạy bot**. Các nút **Chạy tất cả**, **Dừng tất cả** và **Xóa tất cả** nằm trên đầu danh sách. Xóa tất cả cần xác nhận, dừng các bot và xóa cấu hình đã lưu; log cũ được giữ lại. Chọn **Tạo hàng loạt** để nhập tiền tố tên, tiền tố tài khoản, số bắt đầu và số lượng. Ví dụ `bot` + `abc` + số bắt đầu `123`, số lượng `3` tạo `bot 123`/`abc123`, `bot 124`/`abc124`, `bot 125`/`abc125`. Chọn hệ **Ngẫu nhiên cho từng bot** để chia ngẫu nhiên Trái Đất, Namếc và Xayda cho từng tài khoản. Các bot được khởi chạy cách nhau 0,3 giây để giảm tải đăng nhập. Tối đa 50 bot trong ứng dụng.

Bot luôn chạy chế độ tự động chung: làm bước nhiệm vụ mà nó hiểu, đánh quái, nhặt đồ và cộng chỉ số. Mỗi bot hiển thị hành động hiện tại, HP/KI, map, số quái chết quan sát được, số vật phẩm nhặt, số lần gửi lệnh mua và log. Có thể bật lại, dừng hoặc xóa từng bot ở cùng trang. Nút **Tự cuộn** áp dụng cho log; nếu kéo lên xem dòng cũ, vị trí cuộn được giữ khi log mới tới.

Tùy chọn **Tự tạo tài khoản và nhân vật nếu chưa có** được bật mặc định. Bot gửi lệnh đăng ký `42` trước khi đăng nhập, tránh tính một lần đăng nhập sai cho mỗi tài khoản mới theo giới hạn của server. Nếu tài khoản đã tồn tại, bot đăng nhập bằng mật khẩu đã nhập; nếu mật khẩu sai, bot dừng và báo lỗi. Khi tài khoản chưa có nhân vật, bot tạo nhân vật tên `b` cộng 9 ký tự từ mã băm tài khoản, theo hệ đã chọn: Trái Đất, Namếc hoặc Xayda. Cả lô bot dùng hệ đã chọn trong form; có thể sửa hệ tạo nhân vật của từng bot trong tab **Cấu hình** trước khi tài khoản được tạo nhân vật. Hệ của nhân vật đã tồn tại được đọc từ server và không đổi khi sửa cấu hình. Server yêu cầu tên tài khoản dài 4–18 ký tự và mật khẩu dài 5–18 ký tự để đăng ký.

Server khởi tạo nhân vật mới ở nhiệm vụ chính 0. Bot xử lý các bước mở đầu gồm đi tới mũi tên trong nhà, nói chuyện NPC, mở rương và lấy vật phẩm, thu hoạch đậu rồi báo cáo NPC. Nhân vật đã tồn tại giữ nguyên tiến độ nhiệm vụ đã lưu trong database; thay đổi điểm bắt đầu không tự đặt lại tiến độ cũ.

Khi socket mất kết nối hoặc server tạm ngừng, bot tự kết nối lại sau 2, 4, 8, 16 rồi tối đa 30 giây giữa các lần thử. Dashboard hiển thị **RECONNECTING** và ghi lý do trong log. Bấm **Dừng** sẽ hủy cả thời gian chờ retry. Lỗi xác thực tài khoản/mật khẩu dừng bot để tránh đăng nhập sai lặp lại. Khi mở lại chính ứng dụng Bot Manager, bot đã lưu vẫn ở trạng thái **Đã dừng** và cần bấm **Chạy**.

Bot chọn bãi quái theo sức mạnh, sức đánh và cấp quái, chuyển map khi đã đủ sức đánh quái cao hơn, đánh từng mục tiêu đến khi chết rồi chọn quái khác. Bot đọc gói tin vật phẩm rơi và nhặt vật phẩm thuộc về mình, về làng khi chết và cộng tiềm năng theo lựa chọn cộng chỉ số. Khi HP hoặc KI còn tối đa 20%, bot dừng đánh và ăn đậu thần có sẵn trong túi; nếu hết đậu thì về nhà, kiểm tra cây đậu, thu hoạch khi có hạt rồi ăn đậu. Bot tiếp tục khi chỉ số đang hồi đạt ít nhất 60%. Khi thể lực về 0, bot về làng hành tinh của mình (map 0/7/14), chọn NPC shop theo hệ nhân vật, mua Nho xanh ID 212 bằng vàng rồi dùng đến khi thể lực hồi qua 50%; server chỉ cho ăn Nho xanh khi thể lực không quá 50%, mỗi quả hồi 20%. Bot quay về map làm việc trước đó và hiển thị thể lực trong dashboard. Để thêm Nho xanh vào database đang chạy, chạy [`Server/add-nho-xanh-planet-shops.sql`](../Server/add-nho-xanh-planet-shops.sql) một lần; dump mới đã có sẵn mặt hàng này trong shop của cả ba hành tinh. Trong bước nhiệm vụ yêu cầu sử dụng tiềm năng, bot vẫn cộng một điểm kể cả khi cấu hình cộng chỉ số đang tắt. Hành động hiện tại, sức mạnh và tiềm năng đều hiện trên giao diện và trong log. Nếu map có quái nhưng tất cả đã chết, trạng thái ghi rõ đang đứng yên chờ hồi sinh. Bot đọc bước nhiệm vụ từ server, đi tới map được chỉ định bằng `MovementUtility`, đánh quái ở bước chiến đấu và nói chuyện với NPC khi cần báo cáo. Planner kết hợp waypoint với trạm tàu giữa ba hành tinh; nếu một cổng không phản hồi hoặc không có trên map trực tiếp, bot tạm tránh cạnh đó và tìm tuyến khác. Map instance, map sự kiện hoặc lối bị khóa cần điều kiện riêng; bot sẽ báo khi không có tuyến công khai hợp lệ thay vì giả định có thể đi xuyên tới đó. Các nhiệm vụ có thao tác đặc biệt hoặc menu khác cần được bổ sung luật riêng. Bot chỉ mua item thường khác bằng vàng khi cấu hình map/NPC/menu/item và số lượng; việc mua chỉ thực hiện khi shop trả về đúng item. Giao dịch mặc định là giao dịch trống với player ID đã cấu hình.

Bot đã tạo được lưu trong `state/bots.dat`; khi mở lại ứng dụng, bot trở về trạng thái **Đã dừng** và có thể bấm **Chạy** mà không nhập lại. Trên Windows, file lưu được mã hóa bằng DPAPI gắn với tài khoản Windows hiện tại nên không giải mã được dưới tài khoản Windows khác. Trên Linux/macOS, file lưu ở dạng JSON với quyền `0600`; cần bảo vệ tài khoản hệ điều hành và thư mục này. `state/` được bỏ qua bởi Git. Mật khẩu không xuất hiện trong API trả về hoặc file log.

Log của từng bot được lưu trong `logs/bot-<id>.log`, quay vòng ở mức 2 MB với hai bản cũ. Khi mở lại ứng dụng, tối đa 400 dòng gần nhất của file log hiện trong giao diện. Thư mục `logs/` không được đưa lên Git.

`MovementUtility` dùng waypoint trong `ngocrong-clean.sql` và các lựa chọn tàu từ NPC Dr. Brief, Cargo, Cui. Nếu thêm map hoặc đổi đường cổng trên server, cần cập nhật dữ liệu seed; tuyến tới khu riêng tư vẫn phụ thuộc điều kiện vào map của server. Hiện ứng dụng dùng định dạng gói của server trong repo này. Nếu thay giao thức hoặc dữ liệu map trên server, cần cập nhật bộ giải mã và dữ liệu đường đi. Giới hạn 50 bot mỗi ứng dụng để tránh chiếm tài nguyên máy chủ kiểm thử.

## Kiểm tra

```powershell
python -m unittest discover -s tests -v
```

Bộ kiểm tra giả lập server để xác nhận bắt tay phiên, đăng nhập, đăng ký tài khoản, tạo nhân vật, tải map và gửi lệnh đánh quái. Không cần chạy database hay game server thật để chạy kiểm tra này.
