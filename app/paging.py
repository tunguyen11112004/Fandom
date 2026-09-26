from flask import request


def page_of(items, per_page=12, page_key="page"):
    raw = request.args.get(page_key, "1")
    page = int(raw) if str(raw).isdigit() and int(raw) > 0 else 1
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page) if per_page else 1
    page = min(page, pages)
    start = (page - 1) * per_page
    return items[start:start + per_page], page, pages, total
