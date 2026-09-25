"""Featured articles hub (UC-09).

Items come from published contents that an admin marked as featured (UC-23).
"""

from .models import Category, Content


def news_items(world=None, limit=None):
    query = (
        Content.query.join(Category, Category.category_id == Content.category_id)
        .filter(Content.status == "published", Content.is_featured.is_(True))
    )
    if world:
        query = query.filter(Category.slug == world)
    query = query.order_by(Content.release_date.desc(), Content.created_at.desc())
    if limit:
        query = query.limit(limit)
    return [
        {
            "date": (row.release_date or row.created_at.date()).isoformat(),
            "world": row.category.slug,
            "world_name": row.category.name,
            "title": row.title,
            "summary": row.summary or "",
            "source": row.source_name or "Fan Hub Plus",
            "url": f"/explore/{row.slug}",
            "image": row.image_path,
        }
        for row in query.all()
    ]


def featured_worlds():
    rows = (
        Category.query.join(Content, Content.category_id == Category.category_id)
        .filter(Content.status == "published", Content.is_featured.is_(True))
        .with_entities(Category.slug, Category.name)
        .distinct()
        .order_by(Category.name)
        .all()
    )
    return [{"slug": slug, "name": name} for slug, name in rows]
