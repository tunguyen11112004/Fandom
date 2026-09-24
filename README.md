# Fan Hub Plus (Flask + MySQL)

JSON APIs live under **`/api/be/v1`**. Responses are `{ "ok": true, "data": ... }` or `{ "ok": false, "error": "...", "message": "..." }`.  
Auth: `Authorization: Bearer <access_token>`.

The site and the APIs share Laragon MySQL database `fanhubplus` (`DATABASE_URL=mysql+pymysql://root@127.0.0.1:3306/fanhubplus`). Import `sql/fanhubplus_all_in_one.sql` once if the schema is empty.

## Run (Git Bash)

```bash
cd /c/Users/ADMIN/FanHubPlus
source .venv/Scripts/activate
python run.py
```

- http://127.0.0.1:5000
- http://127.0.0.1:5000/health
- http://127.0.0.1:5000/explore
- Site admin (`/admin/login`): `admin@fanhub.plus` / `AdminHub#2026`
- API admin (`POST /api/be/v1/auth/admin/login`): `admin@fanhubplus.com` / `Admin123!` (also works on `/admin/login`)
- Demo member: `mina@fanhub.plus` / `MemberHub#2026`

## API use cases

| UC | Method | Path | Who |
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
| UC-06 Fandoms | GET | `/fandoms` | Public (`is_active` only) |
| UC-07 Explorer | GET | `/contents?q=&category_id=&fandom_id=&genre_id=&type=&year=&sort=` | Public |
| UC-07/09 Detail | GET | `/contents/<id>` | Public (increments views) |
| UC-09 Featured | GET | `/contents/featured` | Public |
| UC-08 Characters | GET | `/characters`, `/characters/<id>` | Public |
| UC-10 Merch | GET | `/merchandise`, `/merchandise/upcoming`, `/merchandise/<id>` | Public (display only) |
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

`sort` for explorer: `latest` | `popular` | `alpha`. Guests may use `q`, `category_id`, `type` only; advanced filters return `login_required`. Drafts and archived rows stay off the public lists.

**BR-09 popularity:** `views + 5*rating_count + round(avg*10) + 3*bookmark_count` (same as `fn_popularity_score`).

**BR-12:** GPS coordinates are accepted on query `lat`/`lng` only and are not stored.

**UC-04:** `GET /me`, `PUT /me/favorites`, `POST /me/avatar` (JPEG/PNG/WebP, ≤2MB).

**UC-06 hub:** `GET /categories/<id>` returns featured, articles, media, characters, merchandise, plus breadcrumbs.

**UC-10 upcoming:** `GET /releases/upcoming`.

**UC-13:** A second POST bookmark removes it; `?type=content|character|merchandise|event`; hidden items return `available: false`.

**UC-21:** `POST /chat/onboarding` `{action: next|skip|set_categories}`.

**UC-24 notices:** console email plus `GET /me/notifications`. Unpublish: `POST /admin/submissions/<id>/unpublish`.


## MySQL (Laragon)

```bash
mysql -u root < sql/fanhubplus_all_in_one.sql
mysql -u root fanhubplus < sql/user_sessions.sql
```

```
DATABASE_URL=mysql+pymysql://root@127.0.0.1:3306/fanhubplus
```
