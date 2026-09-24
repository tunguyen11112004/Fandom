from sqlalchemy import or_

from .models import Category, Content
from .news import news_items
from .series import SERIES, find_series

GUIDE = [
    {
        "text": "Yeah, I can walk you through it. Home is the front desk. Under the search box you've got eight shelves: anime, gaming, movies, TV, K-pop, comics, manga, and cosplay. Tap one if you already know where you're headed. Want me to show you the search next?",
        "links": [{"label": "Take me home", "href": "/"}],
    },
    {
        "text": "Explore is the whole catalog. Type a title, then if it's too much, use the filters underneath: category, genre, year, what kind of thing it is, and how popular it is. You can also sort it newest, most loved, or A to Z. Should I keep going?",
        "links": [{"label": "Open Explore", "href": "/explore"}],
    },
    {
        "text": "News is where I send people who ask what's going on. It's the September anime and manga headlines, and you can split it into just anime or just manga. Every story links out to the original write-up. One more thing after this.",
        "links": [{"label": "Open the news", "href": "/news"}],
    },
    {
        "text": "That's the lay of the land. Members sign in, admins use a separate gate, and merchandise stays on display. Nothing here is for sale. If you tell me a title or a fandom, I'll pull it up. What were you actually looking for?",
        "links": [{"label": "See the map", "href": "/sitemap"}],
    },
]


def _links_for(items):
    return [
        {"label": item.title, "href": f"/explore/{item.slug}"} for item in items[:3]
    ]


def _small_talk(text):
    if any(phrase in text for phrase in ("are you a bot", "are you ai", "are you human", "are you real", "who are you", "your name")):
        return {
            "text": "I'm Mina, on support. I know the big ones cold: One Piece, Naruto, Demon Slayer, Jujutsu Kaisen, the rest of that shelf. I don't have every chapter memorized, but I can point you the right way. What are you after?",
            "links": [],
        }
    if any(word in text.split() for word in ("hi", "hey", "hello", "hiya", "yo")) or text in {"good morning", "good afternoon", "good evening"}:
        return {
            "text": "Hey, you're through to Mina. One Piece kid, Naruto kid, or are you chasing whatever is hot this year?",
            "links": [],
        }
    if any(word in text for word in ("how are you", "how's it going", "hows it going")):
        return {
            "text": "I'm good, thanks for asking. Quiet shift, which is nice. You looking for a title, or did something on the site confuse you?",
            "links": [],
        }
    if any(word in text for word in ("thank", "thanks", "thx", "appreciate")):
        return {
            "text": "Anytime. Ping me if something else comes up.",
            "links": [],
        }
    if any(word in text.split() for word in ("bye", "goodbye", "cya")) or "see you" in text:
        return {
            "text": "Alright, I'll be here if you come back. Take care.",
            "links": [],
        }
    return None


def _faq(text):
    if any(word in text for word in ("bookmark", "save", "account", "sign in", "signin", "login", "log in", "password", "profile", "register", "forgot")):
        return {
            "text": "Members sign in on the Sign in page. The demo member is mina@fanhub.plus, password MemberHub#2026. New people can register, and Forgot password sends a reset link on this demo. Admins do not use that gate. After you sign in you can edit your name and favorite on your profile.",
            "links": [
                {"label": "Sign in", "href": "/login"},
                {"label": "Register", "href": "/register"},
                {"label": "Forgot password", "href": "/forgot"},
            ],
        }
    if "admin" in text:
        return {
            "text": "The admin gate is separate from member sign-in. The demo admin is admin@fanhub.plus, password AdminHub#2026. From there you can see how many members and titles are on the desk. Merchandise still stays display-only.",
            "links": [{"label": "Admin gate", "href": "/admin/login"}],
        }
    if any(word in text for word in ("event", "meetup", "expo", "calendar", "map", "where is the office", "headquarters", "address")):
        return {
            "text": "Meetups are on the Events page: Anime Expo in Los Angeles on 4 Jul 2026, MCM Comic Con in London on 23 Oct 2026, Gamescom in Cologne on 26 Aug 2026, a stadium night in Seoul on 20 Sep 2026, and Comiket in Tokyo on 14 Aug 2026. Headquarters is 800 Wilshire Blvd, Suite 1200, Los Angeles, CA 90017. Email hello@fanhub.plus or call 213 555 0198.",
            "links": [{"label": "Open events", "href": "/events"}],
        }
    if any(word in text for word in ("category", "categories", "shelves", "shelf", "what pages", "what's on", "whats on", "about this", "what is this", "what is fan")):
        return {
            "text": "Fan Hub Plus is a desk for eight worlds: Anime, Gaming, Movies, TV Shows, K-Pop, Comics, Manga, and Cosplay. Home has the sky and the search. Explore is the full catalog with filters. News is the September headlines. The sitemap lists every room.",
            "links": [
                {"label": "Explore", "href": "/explore"},
                {"label": "Sitemap", "href": "/sitemap"},
            ],
        }
    if any(word in text for word in ("buy", "shop", "merch", "price", "ticket", "pay", "purchase")):
        return {
            "text": "We don't sell anything here, so you won't get a cart or a card form. The merch and events are just for looking. If a page made it seem like you could check out, tell me which one and I'll take a look.",
            "links": [],
        }
    if any(word in text for word in ("news", "headline", "what's new", "whats new", "what is new")):
        headlines = news_items()[:2]
        first, second = headlines[0]["title"], headlines[1]["title"]
        return {
            "text": f"A couple of fresh ones: {first}. And {second}. I can open the rest of the desk if you want to skim.",
            "links": [{"label": "Show me the news", "href": "/news"}],
        }
    asking_how = any(word in text.split() for word in ("how", "where", "help"))
    if (
        "filter" in text
        or "sort" in text
        or text in {"search", "find"}
        or (asking_how and ("search" in text or "find" in text))
    ):
        return {
            "text": "Easiest way is the search box on the home page. If you want to narrow it, go to Explore. There's a row of filters for category, genre, year, type, and popularity, plus a sort. What are you trying to pull up?",
            "links": [{"label": "Open Explore", "href": "/explore"}],
        }
    if "sitemap" in text or ("where" in text and "page" in text):
        return {
            "text": "Right now you've got Home, Anime, Manga, Explore, News, Events, Sign in, Register, and the admin gate. The sitemap is the short list of those.",
            "links": [{"label": "Open the sitemap", "href": "/sitemap"}],
        }
    if any(word in text for word in ("dashboard", "my desk", "member desk", "bookmark", "note")):
        return {
            "text": "After you sign in, your name in the header opens your desk. It shows a greeting, what you opened recently, titles from your favorite fandom, and your bookmarks. On a title page, Bookmark saves it and you can leave a short note. Copy link shares the page.",
            "links": [{"label": "Your desk", "href": "/dashboard"}, {"label": "Sign in", "href": "/login"}],
        }
    if any(word in text for word in ("fan piece", "fan post", "submission", "submit", "send a piece")):
        return {
            "text": "Members can send a fan piece from the desk. You need a title, a category, the writing itself, and a check that you have the right to share it. It stays pending until an admin publishes it or sends it back with a reason. If it comes back, revise it and send it again.",
            "links": [{"label": "Send a piece", "href": "/submissions"}],
        }
    if any(word in text for word in ("feedback", "bug", "suggestion", "complaint")):
        return {
            "text": "Feedback is open to guests and members. Pick bug, suggestion, or question. A bug report also asks which page and the steps that show it again. Guests leave an email. The admin desk can mark it new, reviewing, or done.",
            "links": [{"label": "Send feedback", "href": "/feedback"}],
        }
    if any(word in text for word in ("display", "font", "dark mode", "light mode", "text size", "type size")):
        return {
            "text": "Display is on the sign-in page and on your profile. You can switch dark or light and pick a small, medium, or large type size. Members keep that on the account. Guests keep it in this browser.",
            "links": [{"label": "Display", "href": "/display"}, {"label": "Profile", "href": "/profile"}],
        }
    if any(word in text for word in ("samurai", "background", "character", "video", "wind")):
        return {
            "text": "The figure in the sky is an original samurai, not a clip from a series. On Home the quote stays up and the shelf sits lower so you can see him. The other pages do the same: the title stays up, and the cards drop so the full figure shows. Sign-in keeps the form in the middle.",
            "links": [{"label": "Home", "href": "/"}],
        }
    if any(word in text for word in ("popular", "hottest", "top title", "most loved", "what's hot", "whats hot")):
        top = (
            Content.query.filter(Content.published.is_(True))
            .order_by(Content.popularity_score.desc())
            .limit(4)
            .all()
        )
        names = ", ".join(f"{item.title} ({item.popularity_score})" for item in top)
        return {
            "text": f"Right now the highest scores on the shelf are {names}. Popularity runs from 0 to 100. Explore can sort by most popular, or filter Iconic for 90 and up.",
            "links": [{"label": "Most popular", "href": "/explore?sort=popular"}],
        }
    return None


def _series_reply(text):
    hits = find_series(text)
    if not hits and any(
        phrase in text
        for phrase in (
            "hottest",
            "popular manga",
            "best anime",
            "what should i watch",
            "what should i read",
            "recommend",
            "where do i start",
        )
    ):
        names = ", ".join(series["name"] for series in SERIES[:6])
        return {
            "text": f"If you want the ones people still talk about every week: {names}. One Piece and Naruto are the old giants. For something newer, I'd hand you Jujutsu Kaisen, Chainsaw Man, or Dandadan. Which mood are you in?",
            "links": [{"label": "Manga shelf", "href": "/explore?category=manga"}, {"label": "Anime shelf", "href": "/explore?category=anime"}],
        }
    if not hits:
        return None
    series = hits[0]
    item = Content.query.filter(Content.title.ilike(series["name"])).first()
    links = []
    if item:
        links.append({"label": f"Open {series['name']}", "href": f"/explore/{item.slug}"})
    else:
        shelf = "manga" if "manga" in series["kind"] else "anime"
        links.append({"label": "Browse the shelf", "href": f"/explore?category={shelf}"})
    return {
        "text": f"Oh, {series['name']}. That's {series['creator']}, {series['year']}, {series['kind']}. {series['about']} {series['note']} Want a similar one, or is this the one?",
        "links": links,
    }


def _catalog(text):
    like = f"%{text}%"
    matches = (
        Content.query.join(Category)
        .filter(
            or_(
                Content.title.ilike(like),
                Content.genre.ilike(like),
                Content.summary.ilike(like),
                Category.name.ilike(like),
            )
        )
        .order_by(Content.popularity_score.desc())
        .limit(3)
        .all()
    )
    if not matches and len(text) > 2:
        for word in text.split():
            if len(word) < 4:
                continue
            matches = (
                Content.query.filter(Content.title.ilike(f"%{word}%"))
                .order_by(Content.popularity_score.desc())
                .limit(3)
                .all()
            )
            if matches:
                break
    if not matches:
        category = Category.query.filter(Category.name.ilike(like)).first()
        if category:
            matches = (
                Content.query.filter_by(category_id=category.id)
                .order_by(Content.popularity_score.desc())
                .limit(3)
                .all()
            )
    if not matches:
        return None
    if len(matches) == 1:
        item = matches[0]
        text = f"Yeah, we've got {item.title}. It's under {item.category.name}, {item.release_year}. {item.summary} Want me to leave the link here?"
    else:
        names = ", ".join(item.title for item in matches[:-1])
        text = f"I found a few that fit: {names}, and {matches[-1].title}. I'd start with the first one unless you had a different one in mind."
    return {"text": text, "links": _links_for(matches)}


def reply_to(message, guide_step):
    text = " ".join(message.lower().split())
    if any(phrase in text for phrase in ("show me around", "tour", "guide me", "how does this work", "get started", "walk me")):
        return {**GUIDE[0], "guide_step": 1}
    if guide_step and any(word in text for word in ("next", "continue", "yes", "yeah", "yep", "ok", "okay", "sure", "go on")):
        step = min(guide_step, len(GUIDE) - 1)
        done = step >= len(GUIDE) - 1
        return {**GUIDE[step], "guide_step": 0 if done else step + 1}
    if guide_step and any(word in text for word in ("stop", "cancel", "never mind", "nevermind")):
        return {
            "text": "No problem, I'll stop there. Just tell me what you were actually after.",
            "links": [],
            "guide_step": 0,
        }

    found = _small_talk(text) or _faq(text) or _series_reply(text) or _catalog(text)
    if found:
        found["guide_step"] = guide_step
        return found
    return {
        "text": "I can pull a title, walk the eight shelves, explain sign-in, bookmarks, fan pieces, news, or the Los Angeles headquarters. Name a series, or say show me around.",
        "links": [
            {"label": "Explore", "href": "/explore"},
            {"label": "News", "href": "/news"},
            {"label": "Events", "href": "/events"},
        ],
        "guide_step": guide_step,
    }
