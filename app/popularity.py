from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Bookmark, Content, ContentRating

# BR-09 — same formula as fn_popularity_score in the SQL dump:
# views + 5 * rating_count + round(avg * 10) + 3 * bookmark_count


def refresh_content_popularity(db: Session, content_id: int | None) -> None:
    if not content_id:
        return
    content = db.get(Content, content_id)
    if content is None:
        return
    views = int(content.view_count or 0)
    avg, cnt = (
        db.query(func.avg(ContentRating.score), func.count(ContentRating.rating_id))
        .filter(ContentRating.content_id == content_id)
        .one()
    )
    cnt = int(cnt or 0)
    avg_v = float(avg or 0)
    bm = db.query(Bookmark).filter(Bookmark.content_id == content_id).count()
    content.popularity_score = views + cnt * 5 + int(round(avg_v * 10)) + bm * 3
