# Hệ thống kích hoạt độc lập

Thư viện Node.js không có dependency ngoài, dành cho ứng dụng bạn sở hữu hoặc được phép chỉnh sửa. Không tích hợp vào DTMAX, không thay đổi binary gốc và không cấp mã hợp lệ cho cơ chế DTMAX hiện có.

## Thiết kế

- Chữ ký Ed25519: máy cấp mã giữ private key; ứng dụng chỉ có public key.
- Mỗi mã ràng buộc product, khách hàng, device ID, thời gian và danh sách tính năng.
- Device ID Windows là SHA-256 có phân tách ngữ cảnh của MachineGuid. Đây không phải định danh phần cứng không thể giả mạo; Windows cài lại/clone có thể làm thay đổi hoặc trùng mã.
- Thời điểm hết hạn tính bằng milliseconds UTC, tại đúng expiresAt mã hết hiệu lực.
- Danh sách revokedIds phải được ứng dụng cung cấp từ nguồn tin cậy. Không có server thu hồi tự động.

## Máy quản trị: tạo khóa một lần

Yêu cầu Node.js 22+ hoặc phiên bản Node tương thích trong Electron. Chạy từ thư mục dự án:

```powershell
node licensing/cli.cjs init C:\StudioPrivate\license-keys
```

Giữ `issuer.private.pem` chỉ trên máy quản trị; sao lưu an toàn. Tuyệt đối không đưa vào Git, installer hoặc máy khách. Trên Windows cần thiết lập quyền truy cập thư mục bằng ACL của tài khoản quản trị; mode POSIX trong mã không đảm bảo ACL Windows. Công cụ từ chối ghi đè thư mục khóa đã tồn tại.

## Máy khách Windows: lấy mã thiết bị

```powershell
node licensing/cli.cjs device
```

Trả về chuỗi hex 64 ký tự. Khi tích hợp Electron, gọi windowsDeviceId() trong main process; không tin device ID do renderer gửi lên để xác minh.

## Máy quản trị: cấp mã

Tạo `customer.json` với deviceId thật từ máy khách và thời gian hết hạn phù hợp:

```json
{
  "product": "my-studio",
  "customer": "customer-001",
  "deviceId": "THAY_BANG_CHUOI_HEX_64_KY_TU_TU_MAY_KHACH",
  "expiresAt": 1893456000000,
  "features": ["images", "videos"]
}
```

```powershell
node licensing/cli.cjs issue C:\StudioPrivate\license-keys\issuer.private.pem customer.json customer.license
```

Gửi file `customer.license` cho khách. Không gửi private key. Công cụ không ghi đè file license đã tồn tại.

## Tích hợp vào ứng dụng mới

Chỉ đóng gói `license.cjs`, `device-windows.cjs` và public key vào ứng dụng. Không đóng gói CLI cấp mã hoặc private key. Trong main process/backend:

```javascript
const fs = require('node:fs');
const { verifyLicense } = require('./licensing/license.cjs');
const { windowsDeviceId } = require('./licensing/device-windows.cjs');
const publicKey = fs.readFileSync(PUBLIC_KEY_PATH);
function requireLicense(token, feature) {
  const result = verifyLicense(token, {
    publicKey,
    product: 'my-studio',
    deviceId: windowsDeviceId()
  });
  if (!result.ok) throw new Error(`License: ${result.reason}`);
  if (!result.claims.features.includes(feature)) throw new Error('Feature unavailable');
  return result.claims;
}
// Gọi trước mỗi thao tác cần bảo vệ trong main/backend:
// requireLicense(savedToken, 'images');
// await ownedImageProvider.generate(...);
```

PUBLIC_KEY_PATH phải là đường dẫn tin cậy trong bản app của bạn. Không nhận public key, product ID, thời gian hoặc danh sách thu hồi từ renderer. Chỉ lưu token đã verify, trong app.getPath('userData'); kiểm tra lại khi dùng, không chỉ khi mở cửa sổ. Chỉ kiểm tra ở giao diện là không đủ.

Thư viện chưa tạo giao diện nhập mã, backend tạo ảnh/video hoặc máy chủ cấp phép. Bản Windows DTMAX đã đăng trước đó vẫn giữ nguyên.

## Kiểm thử

```powershell
node --test licensing/license.test.cjs
node licensing/cli.cjs verify C:\StudioPrivate\license-keys\app.public.pem my-studio DEVICE_ID customer.license
```

Đã kiểm thử thư viện và CLI trên Linux. Chưa kiểm thử đọc registry, ACL hoặc chạy ứng dụng trên Windows. Kích hoạt offline không ngăn triệt để chỉnh đồng hồ hoặc sửa binary. Để kiểm soát hạn dùng/thu hồi tốt hơn, cần bổ sung máy chủ HTTPS và token ngắn hạn; backend dịch vụ phải kiểm tra entitlement độc lập.
