# Seedance Studio — web thử nghiệm

Mã giao diện mới viết bằng HTML/CSS/JavaScript, lấy cảm hứng từ cấu trúc studio và tông tím/tối của ứng dụng đã phân tích. Chưa phải bản sao chính xác từng trường hoặc hành vi của DTMAX. Không dùng backend DTMAX, không thay đổi bản quyền và không gọi API ngoài.

## Xem ngay

Tải `downloads/seedance-web-preview.zip`, giải nén toàn bộ và mở `index.html` bằng Chrome/Edge. Không cần cài dependency để xem giao diện. Để chạy qua HTTP nếu trình duyệt hạn chế file cục bộ: `python -m http.server 8765 --directory web-demo` từ thư mục repository, sau đó mở cổng 8765 trên máy của bạn.

## Có thể thử

- Chuyển Tổng quan, Tạo ảnh, Tạo video, Cài đặt và Nhật ký.
- Soạn prompt; chọn tỉ lệ, độ phân giải, số lượng và thời lượng video dự kiến.
- Chọn/xoá ảnh tham chiếu (chỉ xem trên máy; không lưu ảnh trong JSON).
- Thêm/xoá/tìm bản nháp. Dữ liệu tự lưu trên trình duyệt nếu localStorage khả dụng.
- Thêm dự án, đổi tên studio, xuất/nhập JSON; nhập có xác nhận thay thế.
- Menu đáp ứng trên điện thoại.

## Chưa hoạt động

Tạo ảnh/video thật, chọn model thực, tài khoản/proxy, quản lý nhân vật, thư viện kết quả, kích hoạt và dịch vụ backend. Các mục chưa có chức năng được ghi rõ trên giao diện. Các thẻ cảm hứng chỉ là hình CSS, không phải kết quả AI. Không nhập API key hoặc mật khẩu vào bản demo.

## Kiểm thử trình duyệt

```sh
cd web-demo
npm ci
npx playwright install chromium
npm test
```

Nếu dùng Chromium có sẵn, đặt CHROMIUM_PATH tới executable trước khi chạy npm test. Bài kiểm thử tự mở HTTP server cục bộ, kiểm tra lưu/tải lại bản nháp, ảnh/video, tìm kiếm, cài đặt, dự án, tham chiếu, nhập/xuất, hiển thị văn bản người dùng và menu điện thoại. Đã kiểm thử trên Chromium/Linux qua HTTP. Môi trường kiểm thử chặn file:// nên chưa xác minh tự động chế độ mở file trực tiếp.

## Đưa lên website

Có thể tải nội dung `index.html` lên dịch vụ hosting tĩnh của bạn. Chưa có địa chỉ website công khai được triển khai tự động trong phiên này.
