# ChatGPT cho Bot Manager

Bot Manager dùng ChatGPT để chọn trang bị, sách kỹ năng, shop, skill, hướng cộng chỉ số và mục tiêu làm nhiệm vụ hoặc luyện sức mạnh. Bot tự xử lý di chuyển, đánh, nhặt và hồi phục bằng logic nhanh hiện có. Phản hồi sau hành động được ghi riêng theo bot tại `ai/memory/` rồi đưa vào lần quyết định sau.

## Kết nối ChatGPT

Trên máy chạy Bot Manager, cài thư viện cho đăng nhập OAuth và lưu phiên bằng Windows Credential Manager:

```powershell
cd 'D:\Code\game nro\Folder Server\bot-manager'
python -m pip install -r ai/requirements-chatgpt.txt
```

Mở trang **Kết nối ChatGPT** ở thanh bên. Xác nhận quyền dùng gói ChatGPT trong trình duyệt, quay lại Bot Manager và chọn model. Chọn **Dùng AI** riêng cho từng bot ngay trên trang đó hoặc trong **Cấu hình** của bot. Nút **GPT tìm hiểu NRO** cho model tìm tài liệu công khai một lần và lưu ghi chú chung; kiến thức đó là tham khảo, các ID map, quái và vật phẩm vẫn lấy từ dữ liệu bot và server. Các bot AI chia sẻ một tài khoản và model, nhưng gửi trạng thái riêng; tối đa bốn lượt GPT đồng thời.

Kết nối này dùng [Sign in with ChatGPT cho ứng dụng mã nguồn mở chạy cục bộ](https://developers.openai.com/siwc/token-sharing-open-source), gọi Responses API bằng OAuth với `store: false`, `stream: true`. Không dùng API key, cookie hay endpoint riêng của trang ChatGPT web. Quyền sử dụng tùy gói và giới hạn tài khoản, có thể xem tại [ChatGPT Settings → Usage](https://chatgpt.com/settings/usage). Khóa mã hóa ngắn lưu trong Windows Credential Manager; token OAuth được mã hóa trong `ai/state/` cùng ID máy và cấu hình, toàn bộ thư mục được bỏ qua trong Git. Bot không thể điều khiển mọi chức năng game bằng GPT: GPT chọn trong các hành động mà Bot Manager hiện hỗ trợ, và lệnh game được kiểm tra trước khi gửi.
