# Tải ứng dụng Windows x64

GitHub Releases chưa truy cập được từ môi trường build. Bản portable được chia thành 3 phần trong thư mục `downloads/` để chuyển qua Git. Đây không phải bản viết lại hoàn toàn; vẫn dùng backend và cơ chế bản quyền gốc.

## Tải xuống

1. Mở https://github.com/tranngoccau020594-bot/AI
2. Bấm **Code → Download ZIP**.
3. Giải nén toàn bộ ZIP: nhấp phải → **Extract All / Giải nén tất cả**.
4. Mở thư mục `downloads` trong thư mục vừa giải nén.
5. Chạy **GHEP-APP-WINDOWS.cmd**. Không chạy từ bên trong cửa sổ ZIP.
6. Chờ dòng **SHA256 OK**. Công cụ tạo `Seedance-AI-1.0.160-windows-x64.exe` trong cùng thư mục.
7. Mở EXE để thử trên Windows x64.

Không cần cài Node.js hoặc Python để ghép file. File CMD dùng `copy /b` và PowerShell `Get-FileHash` có sẵn trên Windows để ghép và kiểm tra, không tự động khởi chạy ứng dụng. Giữ nguyên ba phần `.part01`, `.part02`, `.part03` cạnh file CMD.

## Trạng thái kiểm chứng

- Build Windows x64 thành công; 420 file gốc trong package khớp hash.
- Giao diện khớp mã kiểm tra toàn vẹn trong ứng dụng gốc.
- Ghép lại ba phần khôi phục EXE chính xác từng byte và khớp SHA-256.
- Chưa chạy file CMD, ứng dụng hoặc tạo ảnh/video trên Windows; môi trường build là Linux.
- App chưa ký số; cần bản quyền và tài khoản hợp lệ cho các chức năng gốc.

SHA-256 EXE: `c25d582f1fa3c8c03d194681691fd87f90c25e2f3afc984974e26005539c7d92`
