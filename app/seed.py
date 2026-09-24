from werkzeug.security import generate_password_hash

from . import db
from .models import Category, Content, User

# Freely licensed photos from Wikimedia Commons. Credits stay with each image.
CATEGORY_IMAGES = {
    "anime": ("anime-expo.jpg", "VeganTylor, CC BY-SA 4.0, via Wikimedia Commons"),
    "gaming": ("tokyo-game-show.jpg", "Syced, CC0, via Wikimedia Commons"),
    "movies": ("movies.jpg", "Fred Cherrygarden, CC BY-SA 4.0, via Wikimedia Commons"),
    "tv-shows": ("arcane.jpg", "Super Festivals, CC BY 2.0, via Wikimedia Commons"),
    "k-pop": ("bts-proof.jpg", "NenehTrainer, CC BY 3.0, via Wikimedia Commons"),
    "comics": ("comics.jpg", "Chester, CC BY 2.0, via Wikimedia Commons"),
    "manga": ("manga.jpg", "Marek Ślusarczyk, CC BY 3.0, via Wikimedia Commons"),
    "cosplay": ("armor-build-weekend.jpg", "LostplanetKD73, CC0, via Wikimedia Commons"),
}

CONTENT_IMAGES = {
    "attack-on-titan": ("attack-on-titan.jpg", "LX-Designs, CC BY-SA 2.0, via Wikimedia Commons"),
    "spirited-away": ("spirited-away.jpg", "Carla Lidia, CC BY-SA 4.0, via Wikimedia Commons"),
    "jujutsu-kaisen": ("jujutsu-kaisen.jpg", "Solomon203, CC BY-SA 4.0, via Wikimedia Commons"),
    "breath-of-the-wild": ("breath-of-the-wild.jpg", "Miguel Discart, CC BY-SA 2.0, via Wikimedia Commons"),
    "hades": ("hades.jpg", "LostplanetKD73, CC BY-SA 4.0, via Wikimedia Commons"),
    "celeste": ("celeste.jpg", "Diliff, CC BY-SA 3.0, via Wikimedia Commons"),
    "everything-everywhere": ("everything-everywhere.jpg", "Dietmar Rabich, CC BY-SA 4.0, via Wikimedia Commons"),
    "across-the-spider-verse": ("across-the-spider-verse.jpg", "Jere Keys, CC BY 2.0, via Wikimedia Commons"),
    "parasite": ("parasite.jpg", "Kinocine, CC BY-SA 4.0, via Wikimedia Commons"),
    "arcane": ("arcane.jpg", "Super Festivals, CC BY 2.0, via Wikimedia Commons"),
    "the-bear": ("the-bear.jpg", "Harrison Keely, CC BY 4.0, via Wikimedia Commons"),
    "wednesday": ("wednesday.jpg", "istolethetv, CC BY 2.0, via Wikimedia Commons"),
    "born-pink": ("born-pink.jpg", "Robbie Klinkenberg, CC BY-SA 4.0, via Wikimedia Commons"),
    "get-up": ("get-up.jpg", "TV10, CC BY 3.0, via Wikimedia Commons"),
    "bts-proof": ("bts-proof.jpg", "NenehTrainer, CC BY 3.0, via Wikimedia Commons"),
    "saga": ("saga.jpg", "Pat Loika, CC BY 2.0, via Wikimedia Commons"),
    "ms-marvel": ("ms-marvel.jpg", "Rich.S., CC BY 2.0, via Wikimedia Commons"),
    "watchmen": ("watchmen.jpg", "Pat Loika, CC BY 2.0, via Wikimedia Commons"),
    "one-piece": ("one-piece.jpg", "玄史生, CC0, via Wikimedia Commons"),
    "chainsaw-man": ("chainsaw-man.jpg", "Rjcastillo, CC BY-SA 4.0, via Wikimedia Commons"),
    "witch-hat-atelier": ("manga.jpg", "Marek Ślusarczyk, CC BY 3.0, via Wikimedia Commons"),
    "armor-build-weekend": ("armor-build-weekend.jpg", "LostplanetKD73, CC0, via Wikimedia Commons"),
    "wig-styling-studio": ("wig-styling-studio.jpg", "Joe Crawford, CC BY 2.0, via Wikimedia Commons"),
    "photo-walk-lighting": ("photo-walk-lighting.jpg", "玄史生, CC0, via Wikimedia Commons"),
}

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


def seed_if_empty():
    if Category.query.first():
        return

    categories = {}
    for name, slug, description in CATEGORIES:
        image_path, image_credit = CATEGORY_IMAGES[slug]
        category = Category(
            name=name,
            slug=slug,
            description=description,
            image_path=image_path,
            image_credit=image_credit,
        )
        db.session.add(category)
        categories[slug] = category

    db.session.flush()

    for item in CONTENTS:
        image_path, image_credit = CONTENT_IMAGES[item["slug"]]
        db.session.add(
            Content(
                category_id=categories[item["category"]].id,
                title=item["title"],
                slug=item["slug"],
                content_type=item["content_type"],
                genre=item["genre"],
                summary=item["summary"],
                body=item["body"],
                release_year=item["release_year"],
                popularity_score=item["popularity_score"],
                image_path=image_path,
                image_credit=image_credit,
            )
        )

    db.session.commit()


def seed_users():
    if User.query.first():
        return
    db.session.add(
        User(
            name="Mina Admin",
            email="admin@fanhub.plus",
            password_hash=generate_password_hash("AdminHub#2026", method="pbkdf2:sha256"),
            role="admin",
            verified=True,
        )
    )
    db.session.add(
        User(
            name="Mina",
            email="mina@fanhub.plus",
            password_hash=generate_password_hash("MemberHub#2026", method="pbkdf2:sha256"),
            role="member",
            verified=True,
            favorite="One Piece",
        )
    )
    db.session.commit()
