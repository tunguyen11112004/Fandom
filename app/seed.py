import shutil
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.extensions import db
from app.media import CATEGORY_IMAGES, CONTENT_IMAGES
from app.models import (
    Category,
    CharacterProfile,
    ChatbotFaq,
    Content,
    ContentGenre,
    ContentTimelineEntry,
    Event,
    Fandom,
    Genre,
    MerchandiseImage,
    MerchandiseItem,
    MerchandiseTag,
    Tag,
    User,
    UserCategory,
)
from app.security import hash_password, utcnow

CATEGORIES = [
    (
        "Anime",
        "anime",
        "Series, films, and the communities that keep rewatching them.",
    ),
    (
        "Gaming",
        "gaming",
        "Worlds you play through, speedrun, and argue about for years.",
    ),
    (
        "Movies",
        "movies",
        "Feature films worth a second screening and a longer conversation.",
    ),
    (
        "TV Shows",
        "tv-shows",
        "Serial storytelling, from prestige dramas to comfort rewatches.",
    ),
    (
        "K-Pop",
        "k-pop",
        "Releases, stages, and the fan labor that surrounds them.",
    ),
    (
        "Comics",
        "comics",
        "Panels, runs, and the characters who outlive their first issue.",
    ),
    (
        "Manga",
        "manga",
        "Long-form comics with their own reading order and fandom rituals.",
    ),
    (
        "Cosplay",
        "cosplay",
        "Making, wearing, and photographing the stories fans carry.",
    ),
]

CONTENTS = [
    {
        "category": "anime",
        "title": "Attack on Titan",
        "slug": "attack-on-titan",
        "content_type": "article",
        "genre": "Dark fantasy",
        "release_year": 2013,
        "popularity_score": 96,
        "summary": "A walled city, a disappearing truth, and a fandom that treated every opening as a clue.",
        "body": "Start with the walls, then notice how often the show asks who gets to draw them. This guide walks the major arcs without pretending the ending is simple. It is here for people who want the political thread, the character turns, and a clean way back into the conversation after a long break.",
    },
    {
        "category": "anime",
        "title": "Spirited Away",
        "slug": "spirited-away",
        "content_type": "video",
        "genre": "Fantasy",
        "release_year": 2001,
        "popularity_score": 94,
        "summary": "A bathhouse, a name, and a film people still quote when they talk about growing up.",
        "body": "This trailer-style cut collects the bathhouse sequences fans return to: the first contract, the soot sprites, and the train that crosses still water. Use it as a short re-entry before a full rewatch, or as a way to show someone why the film still anchors the category.",
    },
    {
        "category": "anime",
        "title": "Jujutsu Kaisen",
        "slug": "jujutsu-kaisen",
        "content_type": "audio",
        "genre": "Action",
        "release_year": 2020,
        "popularity_score": 88,
        "summary": "A listening guide to the openings, fights, and jokes that made the series travel so fast.",
        "body": "The clip focuses on how the soundtrack marks a shift from school-club energy to something heavier. It is a companion for people who already know the plot and want the sound of those set pieces, not a recap.",
    },
    {
        "category": "gaming",
        "title": "The Legend of Zelda: Breath of the Wild",
        "slug": "breath-of-the-wild",
        "content_type": "article",
        "genre": "Adventure",
        "release_year": 2017,
        "popularity_score": 97,
        "summary": "An open plateau, a ruined kingdom, and the game that reset what a first hour can be.",
        "body": "This piece stays with the opening hours: climbing, cooking, and learning the map by failing at it. It is written for players who bounced off the combat and missed how much of the game is about attention.",
    },
    {
        "category": "gaming",
        "title": "Hades",
        "slug": "hades",
        "content_type": "video",
        "genre": "Roguelike",
        "release_year": 2020,
        "popularity_score": 90,
        "summary": "Death as a hallway conversation, and a run that gets more personal the more you lose.",
        "body": "A short capture of one escape attempt, kept because the dialogue changes more than the rooms do. Watch it if you want the tone of the House of Hades before you commit to a full playthrough.",
    },
    {
        "category": "gaming",
        "title": "Celeste",
        "slug": "celeste",
        "content_type": "image",
        "genre": "Platformer",
        "release_year": 2018,
        "popularity_score": 86,
        "summary": "A mountain, a mirror, and screenshots from the climbs players still post years later.",
        "body": "The gallery pairs summit shots with the quieter rooms in between. It is a visual index for people who remember the feeling of the game more clearly than the chapter names.",
    },
    {
        "category": "movies",
        "title": "Everything Everywhere All at Once",
        "slug": "everything-everywhere",
        "content_type": "article",
        "genre": "Science fiction",
        "release_year": 2022,
        "popularity_score": 93,
        "summary": "A laundromat, a multiverse, and a family argument that refuses to stay in one genre.",
        "body": "The note here is about the film's middle, where the jokes and the grief occupy the same frame. It assumes you have seen it, and it is meant for the group chat that still cannot agree on which verse mattered.",
    },
    {
        "category": "movies",
        "title": "Spider-Man: Across the Spider-Verse",
        "slug": "across-the-spider-verse",
        "content_type": "video",
        "genre": "Animation",
        "release_year": 2023,
        "popularity_score": 95,
        "summary": "A trailer cut that treats every universe as a different drawing style.",
        "body": "This embed is the public trailer, kept in the hub so the animation shifts are easy to study: comic halftone, sketchbook line, and the moment the score drops out. It is a media item, not a plot summary.",
    },
    {
        "category": "movies",
        "title": "Parasite",
        "slug": "parasite",
        "content_type": "article",
        "genre": "Thriller",
        "release_year": 2019,
        "popularity_score": 92,
        "summary": "Two houses, one rainstorm, and a film that fans still map room by room.",
        "body": "A spatial reading of the stairs, the basement, and the lawn. Written for viewers who want the class structure of the film without a scene-by-scene recap.",
    },
    {
        "category": "tv-shows",
        "title": "Arcane",
        "slug": "arcane",
        "content_type": "video",
        "genre": "Animation",
        "release_year": 2021,
        "popularity_score": 94,
        "summary": "Piltover and Zaun, painted like a music video that forgot to stop being a tragedy.",
        "body": "A scene reel of the sister storyline, chosen because it carries the show even if you have never played the game it comes from. The clip is a doorway, not a substitute for the season.",
    },
    {
        "category": "tv-shows",
        "title": "The Bear",
        "slug": "the-bear",
        "content_type": "article",
        "genre": "Drama",
        "release_year": 2022,
        "popularity_score": 89,
        "summary": "A Chicago kitchen where the ticket rail is also the plot.",
        "body": "This essay stays inside service: who calls the tickets, who apologizes, and why the show's quietest episode is the one fans quote. It is for people who cook and for people who just recognize the noise.",
    },
    {
        "category": "tv-shows",
        "title": "Wednesday",
        "slug": "wednesday",
        "content_type": "image",
        "genre": "Mystery",
        "release_year": 2022,
        "popularity_score": 84,
        "summary": "Nevermore uniforms, a dance that left the platform, and a gallery of the look.",
        "body": "Stills from the first season, arranged around costume and set rather than mystery answers. Useful when you want the visual language of the show without spoiling the case.",
    },
    {
        "category": "k-pop",
        "title": "BLACKPINK Born Pink",
        "slug": "born-pink",
        "content_type": "article",
        "genre": "Performance",
        "release_year": 2022,
        "popularity_score": 91,
        "summary": "A tour notebook: staging choices, fan projects, and the songs that held the set together.",
        "body": "Written from the audience side. It tracks how the set moved between older singles and the album cycle, and what the lightstick ocean looked like from different sections. No setlist spoilers beyond what was public on the night.",
    },
    {
        "category": "k-pop",
        "title": "NewJeans Get Up",
        "slug": "get-up",
        "content_type": "audio",
        "genre": "Pop",
        "release_year": 2023,
        "popularity_score": 90,
        "summary": "A short listening pass through the EP's soft percussion and spoken-word hooks.",
        "body": "Three tracks, discussed as a sequence rather than as singles. The note is about tempo and texture, for listeners who want a way into the record before the choreography videos.",
    },
    {
        "category": "k-pop",
        "title": "BTS Proof",
        "slug": "bts-proof",
        "content_type": "image",
        "genre": "Pop",
        "release_year": 2022,
        "popularity_score": 96,
        "summary": "Anthology artwork and the way a decade of releases got framed as one object.",
        "body": "A gallery of the public cover system: eras separated by color, titles kept readable at thumbnail size. It is a design note for fans comparing anthology packaging, not a discography.",
    },
    {
        "category": "comics",
        "title": "Saga",
        "slug": "saga",
        "content_type": "article",
        "genre": "Space opera",
        "release_year": 2012,
        "popularity_score": 93,
        "summary": "A family on the run, a war that will not stay off the page, and a book people lend carefully.",
        "body": "An on-ramp for the first arc: who is narrating, why the tone can be tender and brutal in the same issue, and where to stop if you are reading with someone new to the series.",
    },
    {
        "category": "comics",
        "title": "Ms. Marvel",
        "slug": "ms-marvel",
        "content_type": "article",
        "genre": "Superhero",
        "release_year": 2014,
        "popularity_score": 85,
        "summary": "Jersey City, fanfiction inside the fiction, and a hero whose first power is paying attention.",
        "body": "Focused on Kamala's early issues: the stretchy powers are the joke and the metaphor, and the supporting cast is the reason the run still gets handed to new readers.",
    },
    {
        "category": "comics",
        "title": "Watchmen",
        "slug": "watchmen",
        "content_type": "article",
        "genre": "Superhero",
        "release_year": 1986,
        "popularity_score": 95,
        "summary": "A twelve-issue argument about costumes, clocks, and who gets to save the city.",
        "body": "A structural guide to the chapter breaks and the supplemental material at the back of each issue. It is for readers who finished the book once and want the grid, not the twist, explained.",
    },
    {
        "category": "manga",
        "title": "One Piece",
        "slug": "one-piece",
        "content_type": "article",
        "genre": "Adventure",
        "release_year": 1997,
        "popularity_score": 98,
        "summary": "A sea that keeps widening, and a reading map for people who think they started too late.",
        "body": "Not a chapter summary. This is a way to enter the East Blue and the first crew without treating a thousand chapters as homework. It names the arcs that change the tone and the ones you can meet later.",
    },
    {
        "category": "manga",
        "title": "Chainsaw Man",
        "slug": "chainsaw-man",
        "content_type": "video",
        "genre": "Action",
        "release_year": 2018,
        "popularity_score": 90,
        "summary": "A devil, a job, and a trailer that sells the mess on purpose.",
        "body": "Public trailer footage for the anime adaptation, placed with the manga entry so readers can see what the adaptation chose to emphasize. The note flags where the comic is meaner and quieter than the preview.",
    },
    {
        "category": "manga",
        "title": "Witch Hat Atelier",
        "slug": "witch-hat-atelier",
        "content_type": "image",
        "genre": "Fantasy",
        "release_year": 2016,
        "popularity_score": 87,
        "summary": "Ink, apprentices, and page layouts that teach magic as a craft.",
        "body": "A look at how the panels explain spellwork without stopping the story. The gallery is for readers who come for the drawing and stay for the rules of the world.",
    },
    {
        "category": "cosplay",
        "title": "Armor build weekend",
        "slug": "armor-build-weekend",
        "content_type": "article",
        "genre": "Craft",
        "release_year": 2024,
        "popularity_score": 78,
        "summary": "Foam, heat, and a two-day plan for a chest plate that survives a convention hallway.",
        "body": "A maker's log from a club build: pattern scaling, the seam that failed on Saturday, and the strap fix that held through Sunday photos. Materials are generic so you can swap brands.",
    },
    {
        "category": "cosplay",
        "title": "Wig styling studio",
        "slug": "wig-styling-studio",
        "content_type": "video",
        "genre": "Craft",
        "release_year": 2023,
        "popularity_score": 74,
        "summary": "Teasing, spikes, and the ten minutes where a wig starts to look like the reference.",
        "body": "A process clip: crimping, teasing at the root, and a hairspray pass that does not collapse the shape. Shot for makers who already own a wig head and want the sequence, not a shopping list.",
    },
    {
        "category": "cosplay",
        "title": "Photo-walk lighting",
        "slug": "photo-walk-lighting",
        "content_type": "image",
        "genre": "Photography",
        "release_year": 2025,
        "popularity_score": 70,
        "summary": "Hallway fluorescents, one reflector, and shots from a fan meetup that had no studio.",
        "body": "Before-and-after frames from an indoor photo walk. The point is placement: where to stand relative to a window, and when to turn the camera away from a busy backdrop.",
    },
]


REF_CATEGORIES = [
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

ALLOWED_TYPES = {"article", "video", "audio", "image", "trailer", "explainer"}


def _genre_row(session: Session, name: str) -> Genre:
    row = session.query(Genre).filter_by(name=name).first()
    if row is None:
        row = Genre(name=name[:60])
        session.add(row)
        session.flush()
    return row


def seed_reference_data(session: Session) -> None:
    if session.query(Category).count() == 0:
        for name, slug, desc in REF_CATEGORIES:
            file_name = CATEGORY_IMAGES.get(slug, (None, None))[0]
            session.add(Category(name=name, slug=slug, description=desc, cover_url=file_name))
        session.flush()
    if session.query(Genre).count() == 0:
        for name in GENRES:
            session.add(Genre(name=name))
    if session.query(Tag).count() == 0:
        for name in TAGS:
            session.add(Tag(name=name))
    if session.query(ChatbotFaq).count() == 0:
        for question, answer, keywords in FAQS:
            session.add(ChatbotFaq(question=question, answer=answer, keywords=keywords, is_active=True))
    session.commit()


def seed_catalog_if_empty(session: Session) -> None:
    if session.query(Content).count() > 0:
        return
    cats = {row.slug: row for row in session.query(Category).all()}
    for item in CONTENTS:
        category = cats.get(item["category"])
        if category is None:
            continue
        media_type = item["content_type"] if item["content_type"] in ALLOWED_TYPES else "article"
        thumb = CONTENT_IMAGES.get(item["slug"], (None, None))[0]
        row = Content(
            category_id=category.category_id,
            title=item["title"],
            slug=item["slug"],
            type=media_type,
            summary=item["summary"][:500],
            body=item["body"],
            thumbnail_url=thumb,
            release_date=date(item["release_year"], 1, 1),
            popularity_score=item["popularity_score"],
            status="published",
            rights_confirmed=True,
        )
        session.add(row)
        session.flush()
        session.add(ContentGenre(content_id=row.content_id, genre_id=_genre_row(session, item["genre"]).genre_id))
    session.commit()


def seed_showcase_if_empty(session: Session) -> None:
    cats = {row.slug: row for row in session.query(Category).all()}
    if not cats:
        return

    fandom_defs = [
        ("anime", "one-piece", "One Piece"),
        ("anime", "demon-slayer", "Demon Slayer"),
        ("gaming", "zelda", "The Legend of Zelda"),
        ("movies", "ghibli", "Studio Ghibli"),
        ("k-pop", "bts", "BTS"),
        ("comics", "watchmen", "Watchmen"),
        ("manga", "chainsaw-man", "Chainsaw Man"),
        ("cosplay", "expo", "Convention floor"),
    ]
    if session.query(Fandom).count() == 0:
        for cat_slug, slug, name in fandom_defs:
            cat = cats.get(cat_slug)
            if cat is None:
                continue
            session.add(Fandom(category_id=cat.category_id, name=name, slug=slug, is_active=True))
        session.flush()

    fandoms = {row.slug: row for row in session.query(Fandom).all()}
    if session.query(CharacterProfile).count() == 0:
        for name, cat_slug, fan_slug, bio in [
            ("Monkey D. Luffy", "anime", "one-piece", "Captain of the Straw Hats. Stretchy, stubborn, and still aiming at the One Piece."),
            ("Tanjiro Kamado", "anime", "demon-slayer", "A kind swordsman who treats every fight as a chance to keep someone human."),
            ("Link", "gaming", "zelda", "The silent traveler who learns Hyrule by climbing it."),
            ("Chihiro Ogino", "movies", "ghibli", "A girl who keeps her name in a bathhouse that wants to take it."),
        ]:
            cat = cats.get(cat_slug)
            fan = fandoms.get(fan_slug)
            if cat is None:
                continue
            session.add(
                CharacterProfile(
                    category_id=cat.category_id,
                    fandom_id=fan.fandom_id if fan else None,
                    name=name,
                    bio=bio,
                )
            )

    limited = session.query(Tag).filter_by(name="Limited Edition").first()
    collectible = session.query(Tag).filter_by(name="Collectible").first()
    preorder = session.query(Tag).filter_by(name="Pre-Order").first()
    if session.query(MerchandiseItem).count() == 0:
        anime = cats.get("anime")
        gaming = cats.get("gaming")
        if anime is not None:
            item = MerchandiseItem(
                category_id=anime.category_id,
                fandom_id=fandoms["one-piece"].fandom_id if "one-piece" in fandoms else None,
                name="Straw Hat display figure",
                description="A shelf piece for the pirate crew. Display only — no checkout on this hub.",
                image_url="one-piece.jpg",
                reference_url="https://en.wikipedia.org/wiki/One_Piece",
                is_upcoming=False,
            )
            session.add(item)
            session.flush()
            session.add(MerchandiseImage(item_id=item.item_id, image_url="one-piece.jpg", caption="Display figure", sort_order=0))
            if limited:
                session.add(MerchandiseTag(item_id=item.item_id, tag_id=limited.tag_id))
            if collectible:
                session.add(MerchandiseTag(item_id=item.item_id, tag_id=collectible.tag_id))
        if gaming is not None:
            item = MerchandiseItem(
                category_id=gaming.category_id,
                fandom_id=fandoms["zelda"].fandom_id if "zelda" in fandoms else None,
                name="Hyrule map print (upcoming)",
                description="A print timed with the next map drop. Listed here so fans can watch the date, not buy it.",
                image_url="breath-of-the-wild.jpg",
                release_date=date(2026, 11, 20),
                is_upcoming=True,
            )
            session.add(item)
            session.flush()
            if preorder:
                session.add(MerchandiseTag(item_id=item.item_id, tag_id=preorder.tag_id))

    if session.query(Event).count() == 0:
        rows = [
            ("Anime Expo", "convention", "Los Angeles", "US", 34.05, -118.24, datetime(2026, 7, 4, 10, 0), "anime", "https://www.anime-expo.org/"),
            ("MCM Comic Con", "convention", "London", "UK", 51.51, -0.13, datetime(2026, 10, 23, 10, 0), "comics", "https://www.mcmcomiccon.com/"),
            ("Gamescom", "convention", "Cologne", "DE", 50.94, 6.96, datetime(2026, 8, 26, 9, 0), "gaming", "https://www.gamescom.global/"),
            ("Stadium night", "screening", "Seoul", "KR", 37.57, 126.98, datetime(2026, 9, 20, 19, 0), "k-pop", None),
            ("Comiket", "convention", "Tokyo", "JP", 35.68, 139.69, datetime(2026, 8, 14, 10, 0), "manga", None),
        ]
        for title, etype, city, country, lat, lng, start, cat_slug, ticket in rows:
            cat = cats.get(cat_slug)
            session.add(
                Event(
                    category_id=cat.category_id if cat else None,
                    title=title,
                    event_type=etype,
                    city=city,
                    country=country,
                    latitude=lat,
                    longitude=lng,
                    start_at=start,
                    ticket_url=ticket,
                    venue=city,
                )
            )

    featured = session.query(Content).filter(Content.status == "published").order_by(Content.popularity_score.desc()).limit(4).all()
    for row in featured:
        row.is_featured = True
    video = session.query(Content).filter_by(slug="spirited-away").first()
    if video is not None and not video.embed_url:
        video.embed_url = "https://www.youtube.com/embed/ByXuk9QqQkk"
        video.source_name = "Studio Ghibli / YouTube"
    session.commit()


def seed_demo_users(session: Session) -> None:
    member = session.query(User).filter_by(email="mina@fanhub.plus").first()
    if member is None:
        member = User(
            name="Mina",
            email="mina@fanhub.plus",
            password_hash=hash_password("MemberHub#2026"),
            role="user",
            is_active=True,
            email_verified_at=utcnow(),
            bio="One Piece",
            theme="dark",
        )
        session.add(member)
        session.flush()
        anime = session.query(Category).filter_by(slug="anime").first()
        if anime is not None:
            session.add(UserCategory(user_id=member.user_id, category_id=anime.category_id))

    admin_email = "admin@fanhub.plus"
    admin = session.query(User).filter_by(email=admin_email).first()
    admin_hash = hash_password("AdminHub#2026")
    if admin is None:
        session.add(
            User(
                name="Fan Hub Admin",
                email=admin_email,
                password_hash=admin_hash,
                role="admin",
                is_active=True,
                email_verified_at=utcnow(),
            )
        )
    else:
        admin.role = "admin"
        admin.is_active = True
        admin.password_hash = admin_hash
        if admin.email_verified_at is None:
            admin.email_verified_at = utcnow()
    session.commit()


def seed_detail_gaps(session: Session) -> None:
    """Fill missing series, characters, merch, and event copy on a database that already has rows."""
    from app.series import CATALOG_SLUGS, IMAGES, SERIES

    catalog_dir = Path("app/static/images/catalog")
    series_dir = Path("app/static/images/series")
    catalog_dir.mkdir(parents=True, exist_ok=True)
    for name, filename in IMAGES.items():
        slug = CATALOG_SLUGS.get(name)
        if not slug:
            continue
        source = series_dir / filename
        target = catalog_dir / f"{slug}.jpg"
        if source.is_file() and not target.is_file():
            shutil.copyfile(source, target)

    by_name = {row["name"]: row for row in SERIES}
    cats = {row.slug: row for row in session.query(Category).all()}
    anime = cats.get("anime")
    manga = cats.get("manga")
    shelf_for = {
        "One Piece": manga,
        "Chainsaw Man": manga,
    }

    def fandom_for(name: str, category: Category | None, blurb: str) -> Fandom | None:
        if category is None:
            return None
        slug = CATALOG_SLUGS[name]
        row = session.query(Fandom).filter_by(slug=slug).first()
        if row is None:
            row = Fandom(
                category_id=category.category_id,
                name=name,
                slug=slug,
                description=blurb[:500],
                cover_url=f"{slug}.jpg",
                is_active=True,
            )
            session.add(row)
            session.flush()
        elif not row.description:
            row.description = blurb[:500]
        return row

    for name, slug in CATALOG_SLUGS.items():
        facts = by_name.get(name)
        if facts is None:
            continue
        category = shelf_for.get(name) or anime
        fan = fandom_for(name, category, facts["about"])
        body = (
            f"{facts['about']}\n\n"
            f"{facts['note']} {facts['creator']} began it in {facts['year']}. "
            f"It lives here as a {facts['kind']} entry under {facts['genre']}, "
            "with the year, the shelf, and a place to rate or bookmark it."
        )
        row = session.query(Content).filter_by(slug=slug).first()
        if row is None:
            if category is None:
                continue
            row = Content(
                category_id=category.category_id,
                fandom_id=fan.fandom_id if fan else None,
                title=name,
                slug=slug,
                type="article",
                summary=facts["about"][:500],
                description=facts["note"][:500],
                body=body,
                thumbnail_url=f"{slug}.jpg",
                source_name=facts["creator"],
                release_date=date(facts["year"], 1, 1),
                popularity_score=80,
                status="published",
                rights_confirmed=True,
            )
            session.add(row)
            session.flush()
            session.add(ContentGenre(content_id=row.content_id, genre_id=_genre_row(session, facts["genre"]).genre_id))
        else:
            if "\n\n" not in (row.body or "") and len(row.body or "") < 520:
                row.body = f"{row.body}\n\n{facts['about']} {facts['note']}"
            if not row.thumbnail_url:
                row.thumbnail_url = f"{slug}.jpg"
            if row.fandom_id is None and fan is not None:
                row.fandom_id = fan.fandom_id
            if row.release_date is None:
                row.release_date = date(facts["year"], 1, 1)
            if not row.source_name:
                row.source_name = facts["creator"]
            if not row.genre_links:
                session.add(ContentGenre(content_id=row.content_id, genre_id=_genre_row(session, facts["genre"]).genre_id))

    characters = [
        ("Monkey D. Luffy", "Straw Hat", "one-piece", "The captain who treats a crew like family and a sea route like a promise. He wants the One Piece, and he will pick a fight with the world government to keep his friends."),
        ("Tanjiro Kamado", "Demon Slayer", "demon-slayer", "A kind older brother who joined the Corps after his family was killed. He still believes Nezuko can come back, and he fights like that hope is a weapon."),
        ("Link", "Hero of Hyrule", "breath-of-the-wild", "The quiet hero who wakes up with a broken memory and a kingdom already in trouble. The page is a place to remember the journey, not a walkthrough."),
        ("Chihiro", "Sen", "spirited-away", "A girl who walks into a spirit bathhouse and has to work her way back to her own name. The story is about courage that looks small until it isn't."),
        ("Naruto Uzumaki", "Hokage", "naruto", "The loud ninja of the Hidden Leaf, carrying a sealed fox and a promise to be recognized. Sasuke is the rival he refuses to give up on."),
        ("Satoru Gojo", "Strongest", "jujutsu-kaisen", "The sorcerer who treats a deadly job like a joke until the moment he doesn't. Students orbit him because he is both a shield and a problem."),
        ("Eren Yeager", "Attack Titan", "attack-on-titan", "A boy who watched a wall fall and decided the world outside was something he had to reach, then something he had to answer for."),
        ("Izuku Midoriya", "Deku", "my-hero-academia", "The kid born without a quirk who inherits one that can break him. He writes notes on every hero he meets and tries to live up to them."),
        ("Denji", "Chainsaw Man", "chainsaw-man", "A devil hunter who wanted a normal life and got a chainsaw heart instead. The story keeps asking what he is willing to trade for a simple wish."),
        ("Anya Forger", "Test subject", "spy-x-family", "The mind-reading child holding a fake family together because she wants to stay. Most of the comedy is her knowing what the adults will not say."),
        ("Son Goku", "Kakarot", "dragon-ball", "A fighter who keeps meeting a stronger opponent and treating that as good news. The long run is tournaments, wishes, and a crew that refuses to stay down."),
        ("Ichigo Kurosaki", "Soul Reaper", "bleach", "A teenager who can see spirits and then has to protect both towns, the living one and the one after it."),
        ("Gon Freecss", "Hunter", "hunter-x-hunter", "A boy who leaves home to find his father and learns the exam is only the first door. Friendship here is real, and so is the cost."),
        ("Light Yagami", "Kira", "death-note", "A student who picks up a notebook that kills and decides he should rewrite the world. The chase with L is the point of the page."),
        ("Frieren", "Elf mage", "frieren", "An elf who outlives the hero's party and only later understands what the journey meant. The story moves slowly on purpose."),
        ("Momo Ayase", "Dandadan", "dandadan", "A girl who believes in ghosts, teams up with a boy who believes in aliens, and finds out both were right."),
    ]
    for name, alias, slug, bio in characters:
        fan = session.query(Fandom).filter_by(slug=slug).first()
        content = session.query(Content).filter_by(slug=slug).first()
        category_id = fan.category_id if fan else (content.category_id if content else None)
        if category_id is None or anime is None:
            category_id = anime.category_id if anime else None
        if category_id is None:
            continue
        row = session.query(CharacterProfile).filter_by(name=name).first()
        portrait = f"{slug}.jpg"
        if row is None:
            session.add(
                CharacterProfile(
                    category_id=category_id,
                    fandom_id=fan.fandom_id if fan else None,
                    name=name,
                    alias=alias,
                    bio=bio,
                    image_url=portrait,
                )
            )
        else:
            if len(row.bio or "") < 160:
                row.bio = bio
            if not row.alias:
                row.alias = alias
            if not row.image_url:
                row.image_url = portrait
            if row.fandom_id is None and fan is not None:
                row.fandom_id = fan.fandom_id

    merch_rows = [
        ("Straw Hat figure (display)", "one-piece", "A display figure of Luffy's hat, filed so fans can see the piece and the fandom it belongs to.\n\nNothing on this page is for sale. The hub only keeps the photo, the tags, and a bookmark if you want it on your desk."),
        ("Hyrule map print (upcoming)", "breath-of-the-wild", "A print timed with the next map drop. Listed here so fans can watch the date, not buy it.\n\nThe release date sits on the item so the upcoming shelf can show it before the day arrives."),
        ("Nezuko ribbon pin", "demon-slayer", "A small display pin based on Nezuko's bamboo and ribbon, kept with the Demon Slayer shelf.\n\nIt is a reference piece only. Bookmark it if you want the item nearby while you browse the series."),
        ("Survey Corps cloak card", "attack-on-titan", "A display card of the Survey Corps wings, stored with the Attack on Titan shelf.\n\nThe page is for looking, tagging, and remembering the series. There is no checkout."),
        ("Hero notebook", "my-hero-academia", "A notebook-style display piece for Deku's hero notes, filed under My Hero Academia.\n\nUse it as a reference on the shelf. The hub does not take orders."),
        ("Death Note replica card", "death-note", "A display card that recalls the notebook, without pretending anyone should use one.\n\nIt sits with the Death Note shelf so the merchandise page is not just two items."),
    ]
    tags = {row.name: row for row in session.query(Tag).all()}
    for name, slug, description in merch_rows:
        fan = session.query(Fandom).filter_by(slug=slug).first()
        content = session.query(Content).filter_by(slug=slug).first()
        category_id = fan.category_id if fan else (content.category_id if content else None)
        if category_id is None:
            continue
        row = session.query(MerchandiseItem).filter_by(name=name).first()
        if row is None:
            row = MerchandiseItem(
                category_id=category_id,
                fandom_id=fan.fandom_id if fan else None,
                name=name,
                description=description,
                image_url=f"{slug}.jpg",
            )
            session.add(row)
            session.flush()
            if not row.images:
                session.add(MerchandiseImage(item_id=row.item_id, image_url=f"{slug}.jpg", caption=name, sort_order=0))
            collectible = tags.get("Collectible")
            if collectible is not None:
                session.add(MerchandiseTag(item_id=row.item_id, tag_id=collectible.tag_id))
        elif len(row.description or "") < 160:
            row.description = description
            if not row.image_url:
                row.image_url = f"{slug}.jpg"

    event_copy = {
        "Anime Expo": "A large anime convention in Los Angeles, with screenings, guest panels, and exhibitor halls. The ticket link leaves this hub.",
        "MCM Comic Con": "A London comic convention covering manga, games, and screen guests. Use it to plan a trip, not to buy a badge here.",
        "Gamescom": "Cologne's games show, listed so players can see the city and the week. Tickets open on the organizer's site.",
        "Stadium night": "An evening screening and fan gathering in Seoul. No ticket link is on file, so the page only keeps the date and the city.",
        "Comiket": "Tokyo's doujin market. The listing is a date and a city for fans who already know the halls.",
    }
    for title, description in event_copy.items():
        row = session.query(Event).filter_by(title=title).first()
        if row is not None and not row.description:
            row.description = description
            if not row.venue or row.venue == row.city:
                row.venue = f"{title} hall"
            if not row.address:
                row.address = row.city

    beats = {
        "one-piece": [
            (1997, "Manga begins", "Eiichiro Oda starts the Straw Hat voyage."),
            (1999, "Anime sets sail", "The weekly anime picks up the same crew."),
            (2024, "Still running", "The story is still the long one fans plan their week around."),
        ],
        "naruto": [
            (1999, "Hidden Leaf", "Naruto Uzumaki starts as the village outcast who wants to be Hokage."),
            (2002, "Anime run", "The series moves from the academy into the bigger ninja wars."),
            (2017, "Next generation", "Boruto continues after the original run."),
        ],
        "demon-slayer": [
            (2016, "The Corps", "Tanjiro joins the Demon Slayer Corps for Nezuko."),
            (2019, "Anime breakout", "The fight animation carries the story past the manga crowd."),
            (2020, "Mugen Train", "The film becomes the event fans still quote."),
        ],
        "attack-on-titan": [
            (2009, "The walls", "The manga opens on a city that thinks the outside is gone."),
            (2013, "Anime premiere", "The first season turns every opening into a clue."),
            (2023, "Final season", "The ending is the beat people still argue about."),
        ],
        "jujutsu-kaisen": [
            (2018, "Curses", "Yuji swallows a finger and the school year gets worse."),
            (2020, "Anime", "The openings and fights travel faster than the chapters."),
            (2023, "Shibuya", "The story stops treating the strongest as untouchable."),
        ],
        "spirited-away": [
            (2001, "Release", "Chihiro walks into the bathhouse and loses her name."),
            (2003, "Academy Award", "The film becomes the one people still recommend first."),
            (2020, "Still quoted", "Fans keep the bathhouse as the growing-up story."),
        ],
        "death-note": [
            (2003, "The notebook", "Light Yagami picks up a book that kills."),
            (2006, "Anime", "The chase with L becomes the version most people meet first."),
            (2017, "New adaptations", "The idea keeps getting retold, and the original chase stays the reference."),
        ],
        "frieren": [
            (2020, "After the quest", "The elf mage starts the story once the demon king is already gone."),
            (2023, "Anime", "The slow pace is the point, and the series finds a wide audience anyway."),
        ],
    }
    for slug, rows in beats.items():
        content = session.query(Content).filter_by(slug=slug).first()
        if content is None or content.timeline:
            continue
        for order, (year, title, description) in enumerate(rows):
            session.add(
                ContentTimelineEntry(
                    content_id=content.content_id,
                    entry_date=date(year, 1, 1),
                    title=title,
                    description=description,
                    sort_order=order,
                )
            )
    session.commit()


def seed_if_empty():
    seed_catalog_if_empty(db.session)


def seed_users():
    seed_demo_users(db.session)
