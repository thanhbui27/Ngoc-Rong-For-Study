# Chạy trên VPS 1 vCPU / 2 GB RAM

## Database

- Kiểm tra DB/container/volume đang có trên VPS trước khi tạo mới. Dùng lại MariaDB tương thích nếu đã có; tách database `ngocrong` và tài khoản DB riêng cho game.
- Cài MariaDB trực tiếp nếu VPS chưa có Docker và chỉ cần DB cho game. Nếu đã có Docker, dùng lại engine hiện có và chỉ chạy một MariaDB.
- Với DB mới, import `ngocrong-clean.sql`. File này giữ schema và dữ liệu mẫu của game, nhưng không chứa tài khoản, nhân vật, gift code hay dữ liệu dịch vụ cũ. Tạo lại file bằng `python tools/make_clean_seed.py` sau khi thay dump nguồn.
- `ngocrong.sql` là dump gốc có tài khoản và nhân vật. Giữ file này riêng tư; chỉ import nếu thực sự cần giữ dữ liệu cũ. Không chạy thử phá hủy trên DB đang dùng.
- Nếu dùng container MariaDB trên VPS 2 GB, bắt đầu với giới hạn RAM 512 MB, `innodb_buffer_pool_size=128M`, `max_connections=32`, log có giới hạn. Điều chỉnh sau khi đo tải.

## Ứng dụng

- `Login/server.ini` và `Server/resources/config/server.properties` phải cùng trỏ tới database và mật khẩu DB. Game server mặc định dùng cổng Login `3105`, cổng game `14445`.
- Pool mặc định: Login giữ 1, tối đa 4; Server giữ 2, tối đa 12. Thay đổi qua `db.pool.*` và `server.hikari.*` trong các file cấu hình.
- Chạy Java từ đúng thư mục `Login` hoặc `Server` vì game đọc tài nguyên theo đường dẫn tương đối. Mức heap khởi đầu: Login `-Xmx192m`, Server `-Xmx768m`; đo RAM thực tế rồi điều chỉnh.
- Trên Linux, cấu hình systemd hoặc trình quản lý tiến trình để khởi động lại game sau bảo trì. Ứng dụng tự khởi động lại bằng `run.bat` chỉ trên Windows.

## Tài khoản cũ

Đăng nhập thành công sẽ tự chuyển mật khẩu dạng cũ sang PBKDF2. Để chuyển cả các tài khoản chưa đăng nhập, dừng game và Login, sao lưu DB, rồi chạy trong thư mục `Login`:

```bash
java -cp Login.jar security.PasswordMigration
java -cp Login.jar security.PasswordMigration --apply
```

Lệnh đầu chỉ đếm; lệnh thứ hai cập nhật những mật khẩu chưa được chuyển. Không ghi mật khẩu ra log. Bản dump gốc vẫn giữ dữ liệu cũ nên tiếp tục bảo vệ riêng file đó.
