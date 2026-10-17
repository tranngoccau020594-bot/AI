# Tài nguyên giao diện gốc — giữ nguyên

`dist/` được chép nguyên byte từ resources.zip người dùng đã gửi, không qua build lại hoặc chỉnh sửa. Bao gồm HTML, JavaScript, CSS, font, logo, icon và dữ liệu chuỗi giao diện. Manifest ghi SHA-256 từng file cùng hash toàn thư mục khớp giá trị trong main.cjs gốc.

```sh
python tools/verify-original-ui.py
```

Chạy từ thư mục gốc repository. Không sửa file trong `original-ui/dist/`. Mọi adapter backend, công cụ phân tích hoặc thay đổi giao diện mới phải ở bên ngoài; chạy verifier trước/sau thay đổi. Nếu cần bản phái sinh, tạo bản riêng và ghi rõ thay đổi, giữ snapshot này để đối chiếu.

Đây là tài nguyên gốc được bảo toàn, chưa phải frontend gốc đã nối với backend mới. JavaScript có phụ thuộc API, dữ liệu chuỗi khi chạy và cơ chế kiểm tra hiện có. Chưa chạy hoặc kiểm chứng đầy đủ các màn hình gốc. Không chuyển bản studio thử nghiệm trước đó thành giao diện gốc và không thay backend ứng dụng đang đóng gói chỉ bằng việc chép thư mục này.
