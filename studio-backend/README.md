# Independent Studio — backend mới 0.2.0

Đây là backend viết mới bằng Python standard library, không dùng module `.pyd`, máy chủ bản quyền hoặc tài khoản DTMAX. Frontend đi kèm là bản web thử nghiệm đã viết riêng, **chưa phải frontend gốc tương thích API đầy đủ**. File Windows DTMAX cũ và ba phần của nó không bị sửa.

## Chạy bản Windows đã đóng gói

Dùng gói Independent Studio mới, không dùng `GHEP-APP-WINDOWS.cmd` của bản DTMAX cũ. Sau khi tải và giải nén toàn bộ bản mới, mở `Independent Studio.exe`. Python runtime nhúng từ các file được cung cấp đã kèm theo, không kèm site-packages hoặc module ứng dụng DTMAX; không phải cài Node.js/Python. Backend chỉ lắng nghe loopback trên cổng ngẫu nhiên. Dữ liệu nằm trong thư mục `backend-data` của Electron userData, tách khỏi hồ sơ DTMAX.

Executable chưa ký số. Đã build/kiểm tra cấu trúc trên Linux, chưa chạy executable Windows hoặc xác minh API trả ảnh thực tế.

## Chạy từ mã nguồn

Yêu cầu Python 3.12+; không cần pip install cho backend:

```powershell
python studio-backend/server.py --data-dir ./studio-data --port 8766
```

Mở `http://127.0.0.1:8766` trên chính máy của bạn. Không chạy file HTML riêng nếu muốn kết nối backend. Không bind public và không coi backend cục bộ này là dịch vụ multi-user.

Nếu phát triển Electron, từ thư mục repository sau khi cài dependency build ở root:

```powershell
node_modules\.bin\electron studio-desktop
```

Chế độ desktop ưu tiên Python nhúng trong `recovered/python-embed`; nếu không có trên Windows, cần lệnh `python` của Python 3.12+. Không sử dụng `recovered/python` chứa backend DTMAX.

## Đã có

- SQLite lưu cấu hình, tên dự án, bản nháp, trạng thái tác vụ và nhật ký.
- Vòng đời `draft → queued → running → succeeded/failed`, cùng `cancelled/cancelling`.
- Gửi/thử lại là thao tác rõ ràng có xác nhận trong giao diện, vì có thể tính phí API.
- Hủy trước khi chạy không gọi nhà cung cấp. Hủy khi đang chạy chỉ ngừng nhận kết quả sau phản hồi; không thể bảo đảm nhà cung cấp ngừng xử lý hoặc hoàn phí.
- Khởi động lại đánh dấu tác vụ đang xử lý là thất bại, không tự gửi lại và tính phí trùng.
- Lưu/xem/tải ảnh trả về, xuất metadata JSON, xóa tác vụ và media đi kèm.
- Kiểm tra Host/Origin và token phiên để giảm rủi ro truy cập từ trang ngoài; không mở CORS.
- Một backend độc quyền mỗi thư mục dữ liệu; bản thứ hai bị từ chối trước khi sửa trạng thái tác vụ.

## Cấu hình API ảnh hợp lệ

Chỉ cấu hình trên máy chạy backend, qua biến môi trường; không gửi key trong chat hoặc đưa vào Git.

| Biến | Ý nghĩa |
| --- | --- |
| `STUDIO_API_BASE` | Mặc định `https://api.openai.com/v1`; có thể đổi sang HTTPS endpoint được cấp quyền |
| `STUDIO_API_KEY` | Khóa truy cập của bạn |
| `STUDIO_IMAGE_MODEL` | Mặc định `gpt-image-1`; cần quyền truy cập model và quota |

Adapter gọi `POST {STUDIO_API_BASE}/images/generations` với `model`, `prompt`, `n`, `size`. Nó yêu cầu `data[].b64_json` chứa PNG/JPEG/WebP. Với tên model bắt đầu `dall-e`, request có thêm `response_format=b64_json`. Không phải mọi API “tương thích OpenAI” đều hỗ trợ hợp đồng này: cần đối chiếu tài liệu/model, số lượng, kích thước và quyền truy cập thực tế.

Kích thước API là kích thước được gửi thật; tỉ lệ dự kiến trên giao diện chỉ là metadata, không tự crop hoặc biến đổi kết quả. Chọn kích thước nhà cung cấp hỗ trợ; API có thể từ chối lựa chọn không phù hợp. Số lượng giới hạn 1–4; ảnh tối đa 30 MB. Mã hiện không tải URL ảnh từ bên ngoài và không theo redirect mang Authorization.

Không có khóa hoặc model: bản nháp vẫn lưu được, nhưng thao tác Gửi trả lỗi 503 và giữ trạng thái nháp. Có cấu hình chỉ chứng minh đủ biến, không chứng minh API đã xác thực hoặc có quota.

## Chưa có

- Adapter tạo video (Gửi trả 501; không tạo video giả).
- Ảnh tham chiếu/edit, quản lý nhân vật, cookie/tài khoản, proxy và kho tài khoản.
- Nhập lại JSON vào backend, chuyển dữ liệu DTMAX hoặc tương thích tất cả endpoint cũ.
- Tích hợp bộ kích hoạt riêng; hiện app độc lập không yêu cầu kích hoạt.
- Chống sửa đồng hồ, multi-user auth, server Internet hoặc phát hiện sử dụng trái phép key từ máy cục bộ.

## API mới

| Endpoint | Chức năng |
| --- | --- |
| `GET /api/health` | Trạng thái backend, cấu hình ảnh, khả năng video |
| `GET /api/session` | Token phiên cục bộ cho frontend cùng origin |
| `GET /api/workspace` | Dự án, cấu hình, tác vụ, nhật ký |
| `PUT /api/workspace` | Lưu dự án và cấu hình; không ghi đè tác vụ |
| `GET /api/jobs` | Danh sách tác vụ |
| `POST /api/jobs` | Tạo bản nháp |
| `POST /api/jobs/{id}/run` | Gửi/thử lại |
| `POST /api/jobs/{id}/cancel` | Hủy |
| `DELETE /api/jobs/{id}` | Xóa tác vụ đã dừng và media |
| `GET /api/media` | Danh sách media |
| `GET /media/{id.ext}` | Nội dung ảnh được lưu |

Ngoài health/session, API cần header `X-Studio-Token` lấy từ session. Endpoint JSON ghi dữ liệu cần Content-Type application/json. Token không phải thông tin cấp phép từ DTMAX.

## Kiểm thử và build

```powershell
python -m unittest discover -s studio-backend -p "test_*.py" -v
node_modules\.bin\electron-builder --config studio-desktop/builder.json --win --x64
```

11 kiểm thử backend đã qua, bao gồm HTTP thật, trạng thái hàng đợi, lưu trữ sau khởi động lại, lỗi/thu hồi tác vụ, provider giả lập chỉ trong test, ngăn lộ lỗi chứa bí mật và chặn truy cập sai Host/Origin/token. Chromium đã kiểm thử kết nối backend thật, lưu bản nháp, tải lại, cài đặt/dự án, lỗi API chưa cấu hình, video chưa hỗ trợ và xóa tác vụ.

Chưa gửi yêu cầu tính phí đến dịch vụ AI thật vì chưa có cấu hình nhà cung cấp. Chưa chạy app Windows; không coi build thành công là chứng minh mọi chức năng hoạt động trên Windows.

Tài khoản/gói ChatGPT không thay thế quyền OpenAI API. Bản mặc định đã nhắm OpenAI API chính thức, nhưng chưa có khóa được nhập nên chưa xác minh tạo ảnh trả phí. Môi trường cloud đã lưu yêu cầu secret `STUDIO_API_KEY` cho `api.openai.com` và hai biến cấu hình mặc định; cần người dùng nhập khóa an toàn, lưu và Publish để áp dụng cho môi trường cloud. Cấu hình cloud không tự truyền sang app Windows trên máy cá nhân.

Kiểm thử giao diện backend (cần Playwright trong web-demo):

```sh
node studio-backend/browser-test.cjs
```

Bài kiểm thử này tự tạo thư mục dữ liệu tạm và tắt mọi biến API trong tiến trình test để tránh gửi yêu cầu tính phí.

## Nhập OpenAI API key trên máy Windows của bạn

Trong gói Windows mới có `OPEN-WITH-OPENAI.cmd`. Đóng cửa sổ Independent Studio đang chạy, rồi mở CMD này và nhập khóa vào lời nhắc ẩn của PowerShell. Nó dùng API mặc định `https://api.openai.com/v1`, model `gpt-image-1`, không ghi khóa vào file và không gửi khóa vào chat. Khóa vẫn tồn tại trong môi trường tiến trình ứng dụng trong phiên chạy để thực hiện yêu cầu. Cách khởi chạy này chưa được chạy thử trên Windows trong môi trường hiện tại.

Mở `Independent Studio.exe` trực tiếp vẫn dùng các biến STUDIO_API_* đã được cấu hình ở Windows; nếu chưa có khóa, có thể dùng mọi tính năng quản lý nhưng Gửi tác vụ sẽ bị từ chối rõ ràng.
