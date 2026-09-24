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


def category_file(slug: str) -> str | None:
    pair = CATEGORY_IMAGES.get(slug)
    return pair[0] if pair else None


def category_credit(slug: str) -> str:
    pair = CATEGORY_IMAGES.get(slug)
    return pair[1] if pair else ""


def content_file(slug: str) -> str | None:
    pair = CONTENT_IMAGES.get(slug)
    return pair[0] if pair else None


def content_credit(slug: str) -> str:
    pair = CONTENT_IMAGES.get(slug)
    return pair[1] if pair else ""
