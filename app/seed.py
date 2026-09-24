from sqlalchemy.orm import Session

from app.models import Category, ChatbotFaq, Genre, Tag

CATEGORIES = [
    ("Anime", "anime", "Japanese animated series and films"),
    ("Gaming", "gaming", "Video games, esports and game culture"),
    ("Movies", "movies", "Feature films and cinema news"),
    ("TV Shows", "tv-shows", "Television series and streaming shows"),
    ("K-Pop", "k-pop", "Korean pop music, idols and groups"),
    ("Comics", "comics", "Western comics and graphic novels"),
    ("Manga", "manga", "Japanese comics and light novels"),
    ("Cosplay", "cosplay", "Costume play, craftsmanship and events"),
]

GENRES = [
    "Action", "Adventure", "Comedy", "Drama", "Fantasy", "Horror",
    "Romance", "Sci-Fi", "Slice of Life", "Thriller", "Music", "Sports",
]

TAGS = [
    "Limited Edition", "Pre-Order", "Collectible", "Exclusive", "Official", "Fan Made", "Trailer", "Soundtrack",
]

FAQS = [
    (
        "What is Fan Hub Plus?",
        "Fan Hub Plus is a portal that brings anime, gaming, movies, TV, K-Pop, comics, manga and cosplay fandoms together in one place.",
        "about platform what is",
    ),
    (
        "How do I bookmark an item?",
        "Log in, open any article, character, video or merchandise item, then click the bookmark icon. You can add a private note too.",
        "bookmark save favorite note",
    ),
    (
        "Can I buy merchandise here?",
        "No. The merchandise showcase is for display and discovery only; there are no orders or payments on this site.",
        "buy merchandise purchase payment",
    ),
    (
        "How do I submit my own article?",
        "Registered users can submit fan content from their dashboard. An administrator reviews it before it is published.",
        "submit fan article content approval",
    ),
]


def seed_reference_data(db: Session) -> None:
    if db.query(Category).count() == 0:
        for name, slug, desc in CATEGORIES:
            db.add(Category(name=name, slug=slug, description=desc))
        db.flush()
    if db.query(Genre).count() == 0:
        for name in GENRES:
            db.add(Genre(name=name))
    if db.query(Tag).count() == 0:
        for name in TAGS:
            db.add(Tag(name=name))
    if db.query(ChatbotFaq).count() == 0:
        for q, a, kw in FAQS:
            db.add(ChatbotFaq(question=q, answer=a, keywords=kw, is_active=True))
    db.commit()
