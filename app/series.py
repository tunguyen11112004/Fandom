"""Core facts Mina can talk about. Short original notes, not chapter recaps."""

SERIES = [
    {
        "name": "One Piece",
        "aliases": ["one piece", "luffy", "straw hat", "zoro", "nami", "oda"],
        "creator": "Eiichiro Oda",
        "year": 1997,
        "kind": "manga, with a long-running anime",
        "genre": "Adventure",
        "about": "A rubber-limbed kid named Luffy sails with the Straw Hats chasing the One Piece, the treasure left by Gol D. Roger.",
        "note": "It is still the giant of the medium: a huge world, a huge crew, and a story that has been running since the late nineties.",
        "accent": "#e23b2f",
    },
    {
        "name": "Naruto",
        "aliases": ["naruto", "sasuke", "sakura", "hokage", "hidden leaf", "boruto", "kishimoto"],
        "creator": "Masashi Kishimoto",
        "year": 1999,
        "kind": "manga and anime",
        "genre": "Action",
        "about": "Naruto Uzumaki is the loud kid in the Hidden Leaf who wants to be Hokage, with a nine-tailed fox sealed inside him and Sasuke as the rival he cannot quit.",
        "note": "The original run is the ninja classic. Boruto continues the next generation.",
        "accent": "#ff7a1a",
    },
    {
        "name": "Demon Slayer",
        "aliases": ["demon slayer", "kimetsu", "tanjiro", "nezuko"],
        "creator": "Koyoharu Gotouge",
        "year": 2016,
        "kind": "manga and anime",
        "genre": "Action",
        "about": "Tanjiro joins the Demon Slayer Corps to turn his sister Nezuko back from a demon and to hunt the one who destroyed their family.",
        "note": "The anime's fight animation is a big reason it blew up past the manga crowd.",
        "accent": "#2f9e6b",
    },
    {
        "name": "Jujutsu Kaisen",
        "aliases": ["jujutsu", "jjk", "gojo", "yuji", "sukuna"],
        "creator": "Gege Akutami",
        "year": 2018,
        "kind": "manga and anime",
        "genre": "Action",
        "about": "Yuji Itadori swallows a cursed finger and ends up sharing a body with Ryomen Sukuna, while Gojo's students fight curses.",
        "note": "It is one of the hottest modern shonen titles, sharp and meaner than it first looks.",
        "accent": "#7b4dff",
    },
    {
        "name": "Attack on Titan",
        "aliases": ["attack on titan", "aot", "eren", "mikasa", "levi"],
        "creator": "Hajime Isayama",
        "year": 2009,
        "kind": "manga and anime",
        "genre": "Dark fantasy",
        "about": "Humanity lives behind walls while Titans eat whoever slips outside. Eren, Mikasa, and Armin start there, and the story does not stay that simple.",
        "note": "The ending is still something fans argue about. The ride up to it changed what a battle series could talk about.",
        "accent": "#8d6a45",
    },
    {
        "name": "My Hero Academia",
        "aliases": ["my hero", "boku no hero", "mha", "deku", "all might", "bakugo"],
        "creator": "Kohei Horikoshi",
        "year": 2014,
        "kind": "manga and anime",
        "genre": "Superhero",
        "about": "In a world where almost everyone has a Quirk, Izuku Midoriya is born without one and still chases All Might's seat as the top hero.",
        "note": "It is the superhero manga that a lot of people used as their door into modern shonen.",
        "accent": "#2f7dff",
    },
    {
        "name": "Chainsaw Man",
        "aliases": ["chainsaw", "denji", "makima", "power"],
        "creator": "Tatsuki Fujimoto",
        "year": 2018,
        "kind": "manga and anime",
        "genre": "Action",
        "about": "Denji is a broke devil hunter who merges with his chainsaw dog, Pochita, and gets pulled into Makima's orbit.",
        "note": "It feels like a dirty joke and a tragedy in the same chapter. Part two keeps that tone and changes the lead's seat.",
        "accent": "#d23b3b",
    },
    {
        "name": "Spy x Family",
        "aliases": ["spy x family", "spy family", "anya", "loid", "yor"],
        "creator": "Tatsuya Endo",
        "year": 2019,
        "kind": "manga and anime",
        "genre": "Comedy",
        "about": "A spy, an assassin, and a telepath kid pretend to be a normal family, and none of them knows the others' secret at the start.",
        "note": "It is the comfort hit. Funny first, and warmer than the premise sounds.",
        "accent": "#e24b8a",
    },
    {
        "name": "Dragon Ball",
        "aliases": ["dragon ball", "goku", "vegeta", "dbz"],
        "creator": "Akira Toriyama",
        "year": 1984,
        "kind": "manga and anime",
        "genre": "Action",
        "about": "Son Goku starts as a kid with a tail looking for the Dragon Balls, and the story grows into the tournament-and-alien fights people mean when they say DBZ.",
        "note": "A lot of later battle manga is still answering this one.",
        "accent": "#f0a202",
    },
    {
        "name": "Bleach",
        "aliases": ["bleach", "ichigo", "rukia"],
        "creator": "Tite Kubo",
        "year": 2001,
        "kind": "manga and anime",
        "genre": "Action",
        "about": "Ichigo Kurosaki borrows Soul Reaper powers from Rukia and ends up in the business of ghosts, Hollows, and the Soul Society.",
        "note": "The Thousand-Year Blood War anime brought a lot of people back to it.",
        "accent": "#111111",
    },
    {
        "name": "Hunter x Hunter",
        "aliases": ["hunter x hunter", "hxh", "gon", "killua"],
        "creator": "Yoshihiro Togashi",
        "year": 1998,
        "kind": "manga and anime",
        "genre": "Adventure",
        "about": "Gon leaves home to become a Hunter like his missing father, and the exams are only the doorway. Killua is the friend who makes the trip matter.",
        "note": "Hiatuses are part of its reputation. The arcs that do exist are why people still wait.",
        "accent": "#3cb44b",
    },
    {
        "name": "Death Note",
        "aliases": ["death note", "light yagami", "l lawliet", "ryuk"],
        "creator": "Tsugumi Ohba and Takeshi Obata",
        "year": 2003,
        "kind": "manga and anime",
        "genre": "Thriller",
        "about": "Light Yagami finds a notebook that kills anyone whose name is written in it, and a detective called L starts closing in.",
        "note": "It is the mind-game series people recommend when someone says they do not like fights.",
        "accent": "#1a1a1a",
    },
    {
        "name": "Frieren",
        "aliases": ["frieren", "sousou no frieren", "beyond journey's end"],
        "creator": "Kanehito Yamada and Tsukasa Abe",
        "year": 2020,
        "kind": "manga and anime",
        "genre": "Fantasy",
        "about": "The demon king is already defeated. Frieren, an elf mage, is late to understand the humans she traveled with, and she sets out again anyway.",
        "note": "Quiet, and one of the most loved newer fantasy anime.",
        "accent": "#7f9cff",
    },
    {
        "name": "Dandadan",
        "aliases": ["dandadan", "dan da dan", "okarun", "momo ayase"],
        "creator": "Yukinobu Tatsu",
        "year": 2021,
        "kind": "manga and anime",
        "genre": "Action",
        "about": "Momo believes in ghosts, Okarun believes in aliens, and both of them turn out to be right in the worst way.",
        "note": "It is chaotic on purpose, and the anime made it one of the current hot titles.",
        "accent": "#ff4d8d",
    },
]


IMAGES = {
    "One Piece": "one-piece.jpg",
    "Naruto": "naruto.jpg",
    "Demon Slayer": "demon-slayer.jpg",
    "Jujutsu Kaisen": "jujutsu-kaisen.jpg",
    "Attack on Titan": "attack-on-titan.jpg",
    "My Hero Academia": "my-hero.jpg",
    "Chainsaw Man": "chainsaw-man.jpg",
    "Spy x Family": "spy-family.jpg",
    "Dragon Ball": "dragon-ball.jpg",
    "Bleach": "bleach.jpg",
    "Hunter x Hunter": "hunter.jpg",
    "Death Note": "death-note.jpg",
    "Frieren": "frieren.jpg",
    "Dandadan": "dandadan.jpg",
}


def with_images(rows):
    ready = []
    for series in rows:
        item = dict(series)
        item["image"] = IMAGES.get(series["name"])
        ready.append(item)
    return ready


def hottest(limit=8):
    rows = SERIES if limit is None else SERIES[:limit]
    return with_images(rows)


def backdrop_images():
    return list(IMAGES.values())


def find_series(text):
    hits = []
    for series in SERIES:
        if any(alias in text for alias in series["aliases"]):
            hits.append(series)
    return hits
