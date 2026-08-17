import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from routers.marketing import _apply_post_media_defaults, _normalize_posts  # noqa: E402


def test_legacy_post_with_single_image_backfills_variants_and_selection():
    post = {
        "id": "post-1",
        "titulo": "Teste",
        "image_url": "https://cdn.example.com/one.png",
    }

    changed = _apply_post_media_defaults(post)

    assert changed is True
    assert post["image_variants"] == ["https://cdn.example.com/one.png"]
    assert post["selected_image_index"] == 0
    assert post["image_url"] == "https://cdn.example.com/one.png"


def test_normalize_posts_preserves_variant_selection_fields():
    brand = {"pilares": ["confiança"]}
    ctx = {"sector": "Indústria", "name": "Empresa"}
    posts = _normalize_posts([
        {
            "id": "post-9",
            "formato": "Post",
            "titulo": "Post com variantes",
            "legenda": "Legenda",
            "hashtags": ["#teste"],
            "cta": "Falar connosco",
            "dia": "segunda",
            "tema": "Tema",
            "objetivo": "leads",
            "pilar": "confiança",
            "image_variants": [
                "https://cdn.example.com/a.png",
                "https://cdn.example.com/b.png",
                "https://cdn.example.com/c.png",
            ],
            "selected_image_index": 2,
        }
    ], brand, ctx)

    post = posts[0]
    assert post["image_variants"][2] == "https://cdn.example.com/c.png"
    assert post["selected_image_index"] == 2
    assert post["image_url"] == "https://cdn.example.com/c.png"