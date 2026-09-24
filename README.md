# FanHubPlus — backend tạm (Flask)

Prefix **`/api/be/v1`**. Response luôn `{ "ok": true, "data": ... }` hoặc `{ "ok": false, "error": "...", "message": "..." }`.  
Auth: `Authorization: Bearer <access_token>`. Frontend có thể gắn sau; hiện tại gọi API trực tiếp.

Dump SQL: `sql/fanhubplus_all_in_one.sql`. Local mặc định SQLite `fanhubplus.db`.

## Chạy (Git Bash)

```bash
cd /c/Users/ADMIN/FanHubPlus
source .venv/Scripts/activate
python -m app.main
```

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/sitemap
- http://127.0.0.1:8000/auth-ui
- QTV: `admin@fanhubplus.com` / `Admin123!`

## API theo Use Case

| UC | Method | Path | Ai gọi |
|---|---|---|---|
| UC-01 Register | POST | `/auth/register` | Visitor |
| UC-01 Verify | GET/POST | `/auth/verify-email` | Visitor |
| UC-01 Resend | POST | `/auth/resend-verification` | Visitor |
| UC-02 Login | POST | `/auth/login` | Member |
| UC-02 Logout | POST | `/auth/logout` | Member |
| UC-02 Refresh | POST | `/auth/refresh` | Member |
| UC-02 Me | GET | `/auth/me` | Member |
| UC-03 Forgot | POST | `/auth/forgot-password` | Visitor |
| UC-03 Reset | POST | `/auth/reset-password` | Visitor |
| UC-05 Admin login | POST | `/auth/admin/login` | Admin |
| UC-16 Profile | PATCH | `/me` | Member |
| UC-16 Favorites | PUT | `/me/favorites` | Member |
| UC-16 Dashboard | GET/PUT | `/me/dashboard` | Member |
| UC-06 Categories | GET | `/categories`, `/categories/<id>/fandoms` | Public |
| UC-06 Fandoms | GET | `/fandoms` | Public (chỉ `is_active`) |
| UC-07 Explorer | GET | `/contents?q=&category_id=&fandom_id=&genre_id=&type=&year=&sort=` | Public |
| UC-07/09 Detail | GET | `/contents/<id>` | Public (tăng view) |
| UC-09 Featured | GET | `/contents/featured` | Public |
| UC-08 Characters | GET | `/characters`, `/characters/<id>` | Public |
| UC-10 Merch | GET | `/merchandise`, `/merchandise/upcoming`, `/merchandise/<id>` | Public (không bán) |
| UC-11/12 Rate | POST | `/contents/<id>/ratings` `{score:1-5}` | Member |
| UC-13 Bookmark | GET/POST | `/bookmarks` | Member |
| UC-13 Note | PATCH | `/bookmarks/<id>` | Member |
| UC-13 Remove | DELETE | `/bookmarks/<id>` | Member |
| UC-13 Share | POST | `/bookmarks/<id>/share` | Member |
| UC-13 Shared | GET | `/bookmarks/shared/<token>` | Public |
| UC-14 Submit | POST/GET | `/submissions` | Member |
| UC-14 Resubmit | PUT | `/submissions/<id>/resubmit` | Member (rejected) |
| UC-15 Feedback | POST | `/feedback` | Public (visitor bắt buộc email) |
| UC-17/18 Events | GET | `/events?city=&event_type=&lat=&lng=&radius_km=` | Public |
| UC-19 Theme | PATCH | `/me` `{theme, font_size}` | Member |
| UC-20/21 Chat | POST | `/chat/sessions`, `/chat/messages` | Public |
| UC-20 History | GET | `/chat/sessions/<token>/history` | Public |
| UC-22 Admin cat/fandom | PUT/POST/DELETE | `/admin/categories/<id>`, `/admin/fandoms` | Admin |
| UC-23 Admin tags | POST/PUT/DELETE | `/admin/tags` | Admin |
| UC-22/23 CRUD content | POST/PUT/DELETE | `/admin/contents` | Admin |
| UC-08 Admin character | POST/PUT/DELETE | `/admin/characters` | Admin |
| UC-10 Admin merch | POST/PUT/DELETE | `/admin/merchandise` | Admin |
| UC-17 Admin event | POST/PUT/DELETE | `/admin/events` | Admin |
| UC-24 Queue | GET | `/admin/submissions` | Admin |
| UC-24 Review | POST | `/admin/submissions/<id>/review` `{decision, reject_reason, tag_ids}` | Admin |
| UC-25 Feedback admin | GET/PATCH/DELETE | `/admin/feedback` | Admin |
| UC-26 Users | GET/PATCH | `/admin/users` | Admin |
| UC-26 Lock | POST | `/admin/users/<id>/lock` `/unlock` | Admin |
| UC-27 FAQ admin | GET/POST/PUT/DELETE | `/admin/faqs` | Admin |
| UC-28 Reports | GET | `/admin/reports/overview` `user-growth` `content-performance` `category-performance` `engagement` `submissions-feedback` | Admin |

`sort` của explorer: `latest` | `popular` | `alpha`. Khách chỉ tìm cơ bản (`q`, `category_id`, `type`); lọc nâng cao trả `login_required`. Draft/archived không ra public.

**BR-09 độ phổ biến:** `views + 5*số_đánh_giá + round(avg*10) + 3*số_bookmark` (trùng `fn_popularity_score`).

**BR-12:** tọa độ GPS chỉ nhận trên query `lat/lng`, không lưu DB.

**UC-04:** `GET /me`, `PUT /me/favorites`, `POST /me/avatar` (JPEG/PNG/WebP, ≤2MB).

**UC-06 hub:** `GET /categories/<id>` trả featured/articles/media/characters/merchandise + breadcrumbs.

**UC-10 upcoming gộp:** `GET /releases/upcoming`.

**UC-13:** POST bookmark lần 2 = bỏ đánh dấu; `?type=content|character|merchandise|event`; mục ẩn hiện `available: false`.

**UC-21:** `POST /chat/onboarding` `{action: next|skip|set_categories}`.

**UC-24 thông báo:** email console + `GET /me/notifications`. Gỡ bài đã xuất bản: `POST /admin/submissions/<id>/unpublish`.


## MySQL

```bash
mysql -u root -p < sql/fanhubplus_all_in_one.sql
mysql -u root -p fanhubplus < sql/user_sessions.sql
```

```
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/fanhubplus
```
