# AI cục bộ cho Bot Manager

AI này chỉ phục vụ Bot Manager. Mã, runtime CPU, model và nhật ký học từ phản hồi đều nằm trong `bot-manager/ai/`. Không cần GPU, Docker hoặc API key.

Model: [Qwen3 1.7B GGUF Q4_K_M](https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF), chạy bằng [llama.cpp](https://github.com/ggml-org/llama.cpp). `install_local_ai.py` tải đúng bản đã ghim và kiểm SHA-256 trước khi dùng. File model và runtime được bỏ qua trong Git.

```powershell
cd 'D:\Code\game nro\Folder Server\bot-manager'
python ai/install_local_ai.py
```

Chọn **AI cục bộ** khi tạo bot hoặc trong tab **Cấu hình**. Bot chia sẻ một model, chỉ gọi AI định kỳ để xem sức mạnh, tiền, trang bị, đồ trong túi, skill, tiến độ nhiệm vụ và shop. Model chọn một ID hành động trong danh sách bot đã kiểm tra; bot tự xử lý di chuyển, đánh, nhặt và hồi phục bằng logic nhanh hiện có. AI có thể chọn tiếp tục nhiệm vụ hoặc luyện sức mạnh trong 5 phút, chọn hướng cộng HP/KI/sức đánh/giáp, đến shop trang bị ở làng hoặc shop sách kỹ năng Uron ở trạm tàu, mua đồ đủ tiền và sức mạnh, mặc đồ, học sách trong túi và chọn skill để đánh. Phản hồi sau hành động được ghi riêng theo bot tại `ai/memory/` rồi đưa vào lần quyết định sau. Đây là học từ ngữ cảnh và kết quả, không phải huấn luyện lại trọng số model.

Runtime chỉ mở `127.0.0.1:18766`, dùng tối đa 2 luồng CPU và một yêu cầu model tại một thời điểm. Model tự bật khi bot ở chế độ AI cần quyết định; dừng bot AI cuối cùng hoặc đổi nó sang chế độ thường sẽ tắt model. Sau 5 phút không có yêu cầu, runtime cũng tự dừng. Tab **Nhật ký AI** trên web hiển thị quyết định, lý do và kết quả; log kỹ thuật nằm trong `ai/local-model.log`. Bot vẫn chạy logic thường nếu model lỗi hoặc không trả lời.
