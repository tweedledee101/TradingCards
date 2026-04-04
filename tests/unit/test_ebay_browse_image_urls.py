"""collect_browse_item_image_urls dedupes primary + thumbnails + additionalImages."""

from backend.scrapers.ebay_scraper import collect_browse_item_image_urls


def test_collect_browse_item_image_urls_order_and_dedupe() -> None:
    item = {
        "image": {"imageUrl": "https://i.ebayimg.com/a.jpg"},
        "thumbnailImages": [
            {"imageUrl": "https://i.ebayimg.com/a.jpg"},
            {"imageUrl": "https://i.ebayimg.com/b.jpg"},
        ],
        "additionalImages": [
            {"imageUrl": "https://i.ebayimg.com/c.jpg"},
        ],
    }
    urls = collect_browse_item_image_urls(item)
    assert urls == [
        "https://i.ebayimg.com/a.jpg",
        "https://i.ebayimg.com/b.jpg",
        "https://i.ebayimg.com/c.jpg",
    ]


def test_collect_browse_item_image_urls_empty() -> None:
    assert collect_browse_item_image_urls({}) == []
