# Independent Studio 0.2.0 — backend mới

Bản này có backend Python viết mới, SQLite và adapter tạo ảnh OpenAI. Không dùng các module ứng dụng hoặc máy chủ bản quyền DTMAX. Giao diện là bản thử nghiệm riêng, **chưa giống hoặc tương thích đầy đủ giao diện DTMAX gốc**. Bản DTMAX đã đăng trước đó không bị sửa.

## Tải Windows x64

1. Tại repository, chọn **Code → Download ZIP** rồi giải nén toàn bộ.
2. Vào **downloads/independent-studio**.
3. Chạy **GHEP-BAN-MOI.cmd**; chờ **SHA256 OK**. Bốn file part mới phải nằm cạnh CMD.
4. Giải nén toàn bộ **Independent-Studio-0.2.0-windows-x64.zip** vừa được tạo.
5. Mở **Independent Studio.exe** để xem giao diện và quản lý bản nháp. Không cần cài Python/Node.js.
6. Muốn dùng OpenAI: đóng app, mở **OPEN-WITH-OPENAI.cmd** cạnh EXE, nhập API key vào lời nhắc ẩn của PowerShell. Không gửi khóa trong chat hoặc GitHub.
7. Model mặc định là **gpt-image-1**. Nhập prompt, chọn kích thước API, lưu nháp rồi bấm **Gửi** ở bảng tác vụ. API có thể tính phí; cần model/quota/quyền truy cập hợp lệ.

Đây là các phần của **ZIP mới**, không phải ba phần EXE DTMAX cũ. Đừng trộn hai bộ. Bạn cũng có thể tải riêng bốn phần và CMD từ [thư mục bản mới](downloads/independent-studio).

## Chức năng và giới hạn

- Dự án, cấu hình, tác vụ và nhật ký lưu SQLite trên máy người dùng.
- Hàng đợi, hủy/thử lại và thư viện ảnh kết nối backend mới.
- Tạo ảnh dùng OpenAI API thật khi đã cấu hình; thiếu key báo lỗi, không giả lập thành công.
- Chưa có tạo video, ảnh tham chiếu, quản lý nhân vật, tài khoản/proxy hoặc tích hợp kích hoạt riêng.
- Bản mới không yêu cầu kích hoạt; điều này không mở khóa hoặc thay đổi app DTMAX gốc.
- 11 kiểm thử backend và luồng trình duyệt đã qua. Gói Windows đã build, đối chiếu source và CRC; **chưa chạy trên Windows và chưa thử yêu cầu OpenAI tính phí**.
- Bộ nhập key trên Windows chưa được chạy thử trong môi trường Linux. Key chỉ được truyền qua môi trường tiến trình trong phiên đó, không ghi vào file bởi launcher.
- Chưa ký số. Các ảnh trong khu vực cảm hứng vẫn là minh họa CSS, không phải kết quả AI.

SHA-256 ZIP mới: `020762c658f96c2ba93ff6d5a58677ff4981a74c9c835ada5f8612c6bc75c35a`

[Mã nguồn backend và hướng dẫn kỹ thuật](studio-backend/README.md). [Source ZIP chạy thử bằng Python](downloads/independent-studio-source.zip).
