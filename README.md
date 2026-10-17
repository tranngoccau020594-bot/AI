> **Bản mới độc lập:** Xem [backend mới](studio-backend/README.md) và [hướng dẫn tải](DOWNLOAD-NEW-STUDIO.md). Bản này dùng backend Python viết mới, không phải backend DTMAX phục dựng mô tả bên dưới.

# DTMAX SEEDANCE — workspace phục dựng

## Trạng thái thực tế

Đã ghép tài nguyên của phiên bản 1.0.160 từ các ZIP được cung cấp, bao gồm giao diện Electron, backend Cython và Python nhúng. Đây là bản phục dựng sử dụng binary gốc, **chưa phải ứng dụng độc lập có toàn bộ mã nguồn**. Không thay đổi kiểm tra bản quyền hoặc giả lập kết quả tạo ảnh/video.

Đã xác minh 477 file bằng SHA-256 sau khi đọc ZIP có kiểm tra CRC. Giao diện cũng khớp hash kiểm tra toàn vẹn nhúng trong main.cjs gốc. Đã tạo executable Windows x64 và kiểm tra 420 file gốc được đóng gói. Chưa chạy Electron/backend hay xác minh tạo ảnh/video: máy phát triển hiện tại là Linux, trong khi backend chỉ hỗ trợ Windows x64 / CPython 3.12. Hash chỉ chứng minh tính nhất quán với file đã gửi, không chứng minh nguồn gốc hay độ an toàn.

## File dự án

- `tools/recover.py`: ghép ZIP và giải ASAR mà không thực thi mã tải lên; từ chối đường dẫn vượt thư mục và ghi đè file khác nội dung.
- `tools/start.cjs`: khởi chạy chế độ phát triển trên Windows x64, dùng Python nhúng. Chưa kiểm chứng chạy trên Windows.
- `analysis/original-contract.json`: danh mục 126 tên thao tác tìm thấy trong giao diện. Đây chưa phải đặc tả đầy đủ của API.
- `analysis/frontend-api-reference.txt`: đoạn khai báo API trong bundle gốc để đối chiếu.
- `analysis/backend-inventory.json`: danh mục và hash các file backend được cung cấp.
- `recovered/`: các tài nguyên được ghép; không đưa vào Git.

Electron 44.9.0 được ghim trong package-lock làm runtime ứng viên; **chưa xác định phiên bản Electron gốc và chưa xác nhận tương thích**.

## Ghép lại từ ZIP

Dùng Python 3.12, truyền tên thực của từng ZIP (các phần trước có cùng tên resources.zip nên cần đổi tên trên máy):

```powershell
python tools/recover.py --out recovered frontend-resources.zip backend-resources.zip locales.zip
python tools/recover.py --verify recovered
```

Nếu bổ sung archive mới làm thay đổi bộ file, dùng thư mục đầu ra mới để bảo toàn manifest cũ. Lặp lại cùng các archive trên cùng thư mục được hỗ trợ.

## Khởi chạy thử trên Windows x64

Yêu cầu Node.js/npm, tài khoản và bản quyền hợp lệ của ứng dụng gốc. Cài Electron từ registry chính thức:

```powershell
npm ci
npm run verify
npm start
```

## Build Windows

```powershell
npm ci
npm run build:win
npm run verify:package
```

Kết quả trong `release/`: bản ZIP và portable EXE. Bản ZIP cần giải nén toàn bộ trước khi mở `Seedance AI.exe`; không lấy riêng EXE khỏi các thư mục đi kèm. Bản portable tự giải nén khi chạy. Chưa ký mã bằng chứng thư nhà phát hành. Runtime mới cung cấp bộ locales riêng, không trộn locales Chromium cũ vào runtime mới.

Trong Linux sandbox, cấu hình cache ở thư mục được ghi trước khi build:

```sh
XDG_CACHE_HOME="$PWD/.cache" ELECTRON_BUILDER_CACHE="$PWD/.cache/electron-builder" npm run build:win
```

Build thành công chỉ xác nhận đóng gói. Các mục phải thử trên Windows: mở cửa sổ và backend, kích hoạt bằng bản quyền hợp lệ, lưu/đọc cấu hình, tạo ảnh thật, tạo video thật, hủy/thử lại tác vụ, xuất media, đóng/mở lại ứng dụng. Media có thể cần FFmpeg bên ngoài; các ZIP được gửi chưa chứa thư mục FFmpeg riêng. Chưa xác minh tự cập nhật với bản đóng gói mới; vẫn có mã cập nhật gốc.

Launcher chạy mã ứng dụng đã gửi. Thực hiện lần đầu trong máy Windows thử nghiệm với tài khoản thử nghiệm. Không đưa API key, cookie hoặc mật khẩu vào Git hay báo cáo lỗi.

Chế độ phát triển dùng đường khởi chạy có sẵn của main.cjs và giữ nguyên cơ chế bản quyền. Chưa tạo installer hoặc tự động cập nhật riêng.

## Điều kiện hoàn thành ứng dụng riêng

1. Chốt Windows desktop hay web và phạm vi được phép tái sử dụng mã/tài nguyên.
2. Có quyền truy cập dịch vụ tạo ảnh/video cùng tài liệu API hoặc mã nguồn backend; cấu hình bí mật ngoài Git.
3. Chốt phiên bản Electron tương thích và chạy thử trên Windows.
4. Ghi lại request/response hợp lệ để hoàn thiện đặc tả, không suy đoán từ tên hàm.
5. Nếu cần backend có thể chỉnh sửa, viết lại từng nhóm: dự án, asset, hàng đợi tác vụ, provider ảnh/video, media, tài khoản, proxy, trợ lý và lưu trữ.
6. Kiểm chứng luồng tạo ảnh/video thật, lỗi/hủy/thử lại, lưu dữ liệu sau khởi động lại, nhập/xuất media và đóng gói trên máy Windows sạch.

Không xem các bước 1–6 là đã hoàn thành. Việc có giao diện và file binary không bảo đảm dịch vụ phía máy chủ của bản gốc còn truy cập được.
