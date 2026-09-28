# Fan Hub Plus

Cổng thông tin fandom: tám danh mục (Anime, Gaming, Movies, TV Shows, K-Pop, Comics, Manga, Cosplay). Khách xem nội dung, thành viên đánh dấu, đánh giá và gửi bài, quản trị viên duyệt và quản lý dữ liệu. Merchandise chỉ trưng bày, không bán hàng.

Bản đang chạy: [https://fanhubplus.onrender.com/](https://fanhubplus.onrender.com/)

## Công nghệ

| Phần | Công nghệ |
|---|---|
| Web | Python 3, Flask, Jinja2, HTML, CSS, JavaScript |
| Dữ liệu | MySQL hoặc MariaDB, SQLAlchemy, Flask-SQLAlchemy, PyMySQL |
| Kiểm tra dữ liệu | Pydantic |
| Đăng nhập | Phiên Flask cho trang web; JWT (PyJWT) cho API `/api/be/v1` |
| Mật khẩu | bcrypt |
| Bản đồ sự kiện | Leaflet, nền bản đồ Esri |
| Email | In ra console khi phát triển, hoặc SMTP khi cấu hình |
| AI | Google Gemini cho chatbot Mina. Không có API key thì Mina trả lời từ FAQ và các câu soạn sẵn trong ứng dụng |
| Host | [Render](https://fanhubplus.onrender.com/) |

Chatbot nằm ở nút Mina góc phải. Khi `GEMINI_API_KEY` có giá trị, câu hỏi được gửi tới Gemini (mặc định model `gemini-3.8-flash`). Câu trả lời bị giới hạn trong nội dung trên hub. Gemini lỗi hoặc không có key thì hệ thống dùng FAQ và hướng dẫn từng bước (duyệt danh mục, tìm kiếm, đánh dấu, sự kiện). Lịch sử chat của khách gắn với phiên trình duyệt; của thành viên gắn với tài khoản.

## Cài đặt trên máy

Cần Python 3.11 trở lên và một máy chủ MySQL hoặc MariaDB (XAMPP, Laragon, hoặc cài riêng).

1. Tải mã nguồn và vào thư mục dự án.
2. Tạo cơ sở dữ liệu và nạp schema (làm một lần):

```bash
mysql -u root -e "CREATE DATABASE IF NOT EXISTS fanhubplus CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root fanhubplus < sql/fanhubplus_all_in_one.sql
```

Nếu máy chủ MySQL có mật khẩu, thêm `-p` sau `root`.

3. Tạo môi trường ảo và cài thư viện.

Windows (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS hoặc Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Sao chép cấu hình:

```bash
copy .env.example .env
```

Trên macOS hoặc Linux dùng `cp .env.example .env`. Sửa `DATABASE_URL` cho đúng user, mật khẩu và cổng MySQL. Đổi `SECRET_KEY` thành một chuỗi dài ngẫu nhiên. Muốn Mina dùng Gemini thì dán khóa từ [Google AI Studio](https://aistudio.google.com/) vào `GEMINI_API_KEY`. Để trống khóa thì chatbot vẫn chạy bằng FAQ.

5. Chạy:

```bash
python run.py
```

Mở http://127.0.0.1:5000. Kiểm tra sống của ứng dụng: http://127.0.0.1:5000/health.

Lần chạy đầu, ứng dụng tạo tài khoản quản trị từ `SEED_ADMIN_EMAIL` và `SEED_ADMIN_PASSWORD` trong `.env` nếu email đó chưa có trong cơ sở dữ liệu.

## Tài khoản dùng thử

Các tài khoản này có trong dữ liệu mẫu của bản local. Bản trên Render dùng cùng loại tài khoản nếu cơ sở dữ liệu đã được nạp dữ liệu mẫu.

| Vai trò | Email | Mật khẩu | Vào đâu |
|---|---|---|---|
| Thành viên | `mina@fanhub.plus` | `MemberHub#2026` | Sign in trên trang web |
| Quản trị | `admin@fanhub.plus` | `AdminHub#2026` | `/admin/login` |
| Quản trị API | `admin@fanhubplus.com` | `Admin123!` | `POST /api/be/v1/auth/admin/login`, cũng đăng nhập được ở `/admin/login` |

## Cách dùng trang web

### Khách

- Trang chủ có sitemap, tám danh mục (tên, mô tả, ảnh bìa) và ô tìm theo từ khóa.
- Explore mở một danh mục: bài nổi bật, bài viết, media, nhân vật, merchandise, kèm breadcrumb.
- Khách tìm theo từ khóa và danh mục. Lọc theo fandom, thể loại, năm, độ phổ biến hoặc sắp xếp nâng cao thì phải đăng nhập; sau khi đăng nhập hệ thống đưa về đúng trang đang xem.
- Media phát video, trailer hoặc audio trên trang. Characters lọc theo danh mục và fandom. Merch chỉ xem, không có giỏ hàng hay thanh toán. Upcoming liệt kê lịch phát hành.
- Events có bản đồ và lịch. Cho phép vị trí thì sự kiện sắp theo khoảng cách; từ chối thì chọn thành phố, loại sự kiện và khoảng ngày. Liên kết vé mở tab mới. Tọa độ không được lưu.
- Nút **A** trên header đổi cỡ chữ. Lựa chọn của khách lưu trên trình duyệt.
- Feedback: chọn lỗi, góp ý hoặc câu hỏi. Báo lỗi thì điền trang và các bước tái hiện. Khách phải để email.
- Nút Mina mở chat.

### Thành viên

Đăng ký bằng họ tên, email và mật khẩu. Mở liên kết xác minh trong email (khi phát triển, nội dung email in ở console). Tài khoản mới sau khi đăng nhập vào form hồ sơ để chọn fandom và danh mục quan tâm. Lần sau vào trang Profile.

- Profile: lời chào, thông báo duyệt bài, hoạt động gần đây, nội dung theo fandom, bookmark và bài đã gửi. **Edit profile** mở form sửa.
- Trên bài, media, nhân vật, merchandise hoặc sự kiện: đánh dấu, ghi chú, bỏ đánh dấu. Đánh giá media từ 1 đến 5 sao, mỗi người một đánh giá và được sửa.
- Contribute: gửi bài fan (tiêu đề, danh mục, fandom, nội dung, ảnh hoặc media). Phải xác nhận có quyền chia sẻ. Bài ở trạng thái chờ duyệt. What you sent theo dõi trạng thái; bài bị từ chối xem được lý do rồi sửa và gửi lại.
- Cỡ chữ và giao diện của thành viên lưu theo tài khoản.

### Quản trị

Vào `/admin/login`. Thành viên mở thẳng URL quản trị sẽ bị từ chối.

- Dashboard: số liệu sử dụng, lọc theo khoảng thời gian.
- Categories: thêm, sửa tên, mô tả và ảnh bìa (dán link hoặc tải file). Xóa chỉ khi danh mục chưa được dùng.
- Fandoms, Catalog, Characters, Merchandise, Events, Tags, FAQ: thêm, sửa, ẩn hoặc xóa. Bài ẩn không còn trên trang công khai.
- Review: hàng đợi bài fan, cũ hơn trước. Duyệt để xuất bản, hoặc từ chối kèm lý do. Người gửi nhận thông báo.
- Feedback: lọc theo loại và trạng thái, cập nhật trạng thái, xóa phản hồi.
- Members: tìm thành viên, khóa hoặc mở khóa. Tài khoản bị khóa không đăng nhập được.
- Record: nhật ký thao tác quản trị.

## API

Trang web và API dùng chung cơ sở dữ liệu. API JSON nằm dưới `/api/be/v1`, xác thực bằng `Authorization: Bearer <access_token>`. Phản hồi dạng `{ "ok": true, "data": ... }` hoặc `{ "ok": false, "error": "...", "message": "..." }`.
