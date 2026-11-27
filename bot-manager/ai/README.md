# AI cục bộ cho Bot Manager

AI này chỉ phục vụ Bot Manager. Mã, runtime CPU, model và nhật ký học từ phản hồi đều nằm trong `bot-manager/ai/`. Không cần GPU, Docker hoặc API key.

Model: [Qwen3 1.7B GGUF Q4_K_M](https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF), chạy bằng [llama.cpp](https://github.com/ggml-org/llama.cpp). `install_local_ai.py` tải đúng bản đã ghim và kiểm SHA-256 trước khi dùng. File model và runtime được bỏ qua trong Git.

```powershell
cd 'D:\Code\game nro\Folder Server\bot-manager'
python ai/install_local_ai.py
```

Chọn **AI cục bộ** khi tạo bot hoặc trong tab **Cấu hình**. Bot chia sẻ một model, chỉ gọi AI định kỳ để xem sức mạnh, tiền, trang bị, đồ trong túi, skill, tiến độ nhiệm vụ và shop. Model chọn một ID hành động trong danh sách bot đã kiểm tra; bot tự xử lý di chuyển, đánh, nhặt và hồi phục bằng logic nhanh hiện có. AI có thể chọn tiếp tục nhiệm vụ hoặc luyện sức mạnh trong 5 phút, chọn hướng cộng HP/KI/sức đánh/giáp, đến shop trang bị ở làng hoặc shop sách kỹ năng Uron ở trạm tàu, mua đồ đủ tiền và sức mạnh, mặc đồ, học sách trong túi và chọn skill để đánh. Phản hồi sau hành động được ghi riêng theo bot tại `ai/memory/` rồi đưa vào lần quyết định sau. Đây là học từ ngữ cảnh và kết quả, không phải huấn luyện lại trọng số model.

Runtime chỉ mở `127.0.0.1:18766`, dùng tối đa 2 luồng CPU và một yêu cầu model tại một thời điểm. Model tự bật khi bot ở chế độ AI cần quyết định; dừng bot AI cuối cùng hoặc đổi nó sang chế độ thường sẽ tắt model. Sau 5 phút không có yêu cầu, runtime cũng tự dừng. Tab **Nhật ký AI** trên web hiển thị quyết định, lý do và kết quả; log kỹ thuật nằm trong `ai/local-model.log`. Bot vẫn chạy logic thường nếu model lỗi hoặc không trả lời.

## Dùng gói ChatGPT thay cho model CPU

Trên máy chạy Bot Manager, cài thư viện cho đăng nhập OAuth và lưu phiên bằng Windows Credential Manager:

```powershell
cd 'D:\Code\game nro\Folder Server\bot-manager'
python -m pip install -r ai/requirements-chatgpt.txt
```

Mở trang **Kết nối ChatGPT** ở thanh bên. Xác nhận quyền dùng gói ChatGPT trong trình duyệt, quay lại Bot Manager và chọn model. Chọn **Dùng AI** riêng cho từng bot ngay trên trang đó hoặc trong **Cấu hình** của bot. Nút **GPT tìm hiểu NRO** cho model tìm tài liệu công khai một lần và lưu ghi chú chung; kiến thức đó là tham khảo, các ID map, quái và vật phẩm vẫn lấy từ dữ liệu bot và server. Các bot AI chia sẻ một tài khoản và model, nhưng gửi trạng thái riêng; tối đa bốn lượt GPT đồng thời. Bot tự chạy logic đánh, di chuyển và nhặt đồ giữa các lần GPT quyết định. Dùng **Dùng model cục bộ** để trở lại CPU, không cần đăng xuất.

Kết nối này dùng [Sign in with ChatGPT cho ứng dụng mã nguồn mở chạy cục bộ](https://developers.openai.com/siwc/token-sharing-open-source), gọi Responses API bằng OAuth với `store: false`, `stream: true`. Không dùng API key, cookie hay endpoint riêng của trang ChatGPT web. Quyền sử dụng tùy gói và giới hạn tài khoản, có thể xem tại [ChatGPT Settings → Usage](https://chatgpt.com/settings/usage). Khóa mã hóa ngắn lưu trong Windows Credential Manager; token OAuth được mã hóa trong `ai/state/` cùng ID máy và cấu hình, toàn bộ thư mục được bỏ qua trong Git. Bot không thể điều khiển mọi chức năng game bằng GPT: GPT chọn trong các hành động mà Bot Manager hiện hỗ trợ, và lệnh game được kiểm tra trước khi gửi.