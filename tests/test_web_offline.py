"""contaix.web without a network (addaix/contaix#31): nav extraction, page cache, RSC parsing, title de-dup."""

import pytest

from contaix import web
from contaix.web import (
    _strip_duplicate_title,
    extract_site_nav,
    fetch_page,
    is_nextjs_site,
    parse_rsc_flight,
    url_to_cache_key,
)

NAV_HTML = """
<html><body><nav>
<a href="/docs/en/intro">Intro</a>
<a href="/docs/en/guide/setup">Setup</a>
<a href="/docs/en/intro">Intro again</a>
<a href="/blog/post">Blog</a>
<a href="https://other.example/docs/en/x">Elsewhere</a>
<a href="relative.html">Relative</a>
<a href="/docs/en/empty"></a>
</nav></body></html>
"""


def test_url_to_cache_key_is_filesystem_safe():
    assert url_to_cache_key("https://example.com/docs/en/foo/") == "example.com__docs__en__foo.html"
    assert "/" not in url_to_cache_key("http://h:8080/a/b")


def test_is_nextjs_site():
    assert is_nextjs_site("<script>self.__next_f.push([1,'x'])</script>")
    assert not is_nextjs_site("<html></html>")


def test_extract_site_nav_html_fallback_keeps_only_same_site_doc_links_once():
    nav = extract_site_nav("https://example.com/docs/en/home", html=NAV_HTML)
    assert nav["base_url"] == "https://example.com"
    paths = [p["path"] for p in nav["pages"]]
    assert paths == ["/docs/en/intro", "/docs/en/guide/setup"]
    by_path = {p["path"]: p for p in nav["pages"]}
    assert by_path["/docs/en/guide/setup"]["group"] == "Guide"
    assert by_path["/docs/en/intro"]["group"] == ""


def test_fetch_page_caches_and_force_refetches(tmp_path, monkeypatch):
    calls = []

    def fake_fetch(url, *, timeout=None):
        calls.append(url)
        return f"<p>v{len(calls)}</p>"

    monkeypatch.setattr(web, "_fetch_html", fake_fetch)
    url = "https://example.com/a"
    assert fetch_page(url, cache_dir=str(tmp_path)) == "<p>v1</p>"
    assert fetch_page(url, cache_dir=str(tmp_path)) == "<p>v1</p>"  # from cache
    assert len(calls) == 1
    assert fetch_page(url, cache_dir=str(tmp_path), force=True) == "<p>v2</p>"
    assert fetch_page(url) == "<p>v3</p>"  # no cache_dir: always fetches


def test_parse_rsc_flight_reads_json_text_chunks_and_skips_imports():
    text = '1:I["mod",[],"x"]\n2:{"a":1}\n3:T5,hello\n4:not json'
    reg = parse_rsc_flight(text)
    assert reg == {"2": {"a": 1}, "3": "hello"}


def test_parse_rsc_flight_t_chunk_with_code_block_becomes_text():
    raw = "<pre><code>print(1)</code></pre>"
    text = f"1:T{len(raw):x},{raw}\n"
    assert "print(1)" in parse_rsc_flight(text)["1"]


@pytest.mark.parametrize(
    "content,title,expected",
    [
        ("# Hello World\n\nBody", "hello world", "Body"),
        ("# Other\n\nBody", "Hello", "# Other\n\nBody"),
        ("Body only", "Hello", "Body only"),
        ("# Hello\n\nBody", "", "# Hello\n\nBody"),
    ],
)
def test_strip_duplicate_title(content, title, expected):
    assert _strip_duplicate_title(content, title) == expected


def test_auto_extract_prefers_main_content_for_plain_html():
    body = "word " * 60
    html = f"<html><body><nav>menu</nav><main><h1>T</h1><p>{body}</p></main></body></html>"
    out = web._auto_extract_content(html)
    assert "word" in out and "menu" not in out
