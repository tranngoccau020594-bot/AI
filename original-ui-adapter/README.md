# Thử nối giao diện gốc — kết quả có giới hạn

**Trạng thái: tải được màn hình kích hoạt gốc; chưa vào được studio. Không phải bản tích hợp hoàn chỉnh.**

## Đã thực hiện

- Giữ nguyên 12 file trong `original-ui/dist/`; kiểm tra khớp SHA-256 của snapshot và hash nhúng trong main.cjs gốc.
- Chép trực tiếp các response JS/CSS/font/logo từ snapshot, không build lại hoặc sửa bundle.
- Tạo HTML host và bootstrap riêng bên ngoài tài nguyên gốc. Bootstrap chỉ dùng chuỗi công khai trong `chuoi-mo.json`, cộng một số đường dẫn API mới suy ra từ tên hàm; không giải mã chuỗi được bảo vệ hoặc giả lập trạng thái kích hoạt.
- Đọc health, metadata tác vụ/nhật ký/media từ backend mới qua lớp thử nghiệm. Hợp đồng JSON của các bảng studio gốc chưa được xác minh.
- Tất cả POST/PUT/DELETE bị từ chối 501. Backend worker không khởi chạy ở chế độ này; không gửi yêu cầu OpenAI có tính phí.
- CSP giới hạn kết nối về cùng origin; không chuyển thông tin đến máy chủ bản quyền hoặc dịch vụ ngoài.

## Kết quả Chromium đã quan sát

1. Mở nguyên HTML gốc không có bootstrap của server cũ: bundle báo `__S is not defined`.
2. Với host/bootstrap công khai: bundle không có lỗi JavaScript, hiển thị màn hình kích hoạt DTMAX SEEDANCE v1.0.160.
3. Request đầu tiên quan sát được là `GET /api/machine-id`; adapter trả 501 vì chưa triển khai hợp đồng nhận diện máy gốc. Giao diện hiển thị “Không kết nối được license-server”. **Thông báo này không chứng minh máy chủ nhà phát hành đang hỏng**; trong thử nghiệm, endpoint nhận diện máy chưa có.
4. Các bảng chuỗi và các phụ thuộc xác minh/kích hoạt gốc chưa được cung cấp. Chưa kiểm chứng các tab studio, tạo ảnh/video hoặc chức năng tài khoản của giao diện gốc.

Xem `browser-report.json` và `original-ui-preview.png`. Không đặt cờ thành công, không thay public key, không cấp token hoặc giả chữ ký bản quyền để đi qua màn hình này.

## Chạy thử

Yêu cầu Python 3.12+, không cần pip dependency:

```sh
python original-ui-adapter/server.py --data-dir ./original-probe-data --port 8770
```

Mở cổng 8770 trên chính máy đó. Chế độ raw phục vụ HTML gốc không bootstrap bằng cách thêm `--raw`. Server chỉ bind 127.0.0.1.

**Luôn dùng thư mục dữ liệu thử nghiệm mới, tách riêng.** Không trỏ vào dữ liệu production của backend mới: lớp Studio khởi tạo schema và xử lý các trạng thái tác vụ tồn đọng khi mở database. Nhãn “read-only” ở đây mô tả các HTTP endpoint bị chặn ghi, không có nghĩa mở database bất kỳ là không tạo hoặc sửa file.

Trên Windows có thể dùng `START-ORIGINAL-UI.cmd` trong thư mục này sau khi cài Python. Chưa thử script đó trên Windows.

## Kiểm thử

```sh
python -m unittest discover -s original-ui-adapter -p "test_*.py" -v
python tools/verify-original-ui.py
```

Kiểm thử trình duyệt cần Playwright đã cài trong `web-demo`:

```sh
cd web-demo
npm ci
npx playwright install chromium
cd ..
node original-ui-adapter/browser-probe.cjs
```

Có thể đặt CHROMIUM_PATH nếu sử dụng Chromium có sẵn. Probe tự tạo dữ liệu tạm, chặn mọi request ngoài loopback, tắt biến API và xuất báo cáo; nó kiểm tra đúng màn hình kích hoạt, **không đánh dấu studio là đã chạy**.

Để tiếp tục tích hợp studio gốc, cần hợp đồng API/dữ liệu runtime được phép sử dụng và luồng kích hoạt hợp lệ do chủ phần mềm cung cấp. Nếu thiếu các điều kiện đó, có thể tiếp tục backend độc lập, nhưng không thể gọi lớp thử nghiệm này là bản thay backend gốc đã hoàn thành.
