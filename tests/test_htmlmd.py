"""The light html -> markdown path and the sanitiser for untrusted html."""

import subprocess
import sys

from contaix.htmlmd import html_to_clean_markdown, sanitize_html


def test_importing_htmlmd_does_not_pull_the_heavy_stack():
    code = (
        "import sys, contaix.htmlmd;"
        "heavy = {'pandas', 'numpy', 'nbconvert', 'contaix.markdown', 'contaix.web'};"
        "print(sorted(heavy & set(sys.modules)))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == "[]"


def test_web_still_exports_the_same_function():
    from contaix.web import html_to_clean_markdown as via_web

    assert via_web is html_to_clean_markdown


def test_sanitize_drops_everything_live():
    dirty = (
        '<html><head><title>t</title></head><body onload="x()">'
        '<script>evil()</script><iframe src="http://e"></iframe>'
        '<form action="/p"><input name=q></form>'
        '<h1 class="c" id="i" onclick="x()">Title</h1>'
        '<a href="javascript:alert(1)">bad</a><a href="https://ok.example/">good</a>'
        '<img src="http://e/track.png" alt="a cat"></body></html>'
    )
    out = sanitize_html(dirty)
    for bad in ("script", "iframe", "form", "input", "onclick", "onload", "class", "javascript", "<img", "track.png"):
        assert bad not in out
    assert "<h1>Title</h1>" in out
    assert '<a href="https://ok.example/">good</a>' in out
    assert "a cat" in out


def test_sanitize_closes_unbalanced_tags_and_bounds_depth_and_spans():
    assert sanitize_html("<div><p>unclosed") == "<div><p>unclosed</p></div>"
    deep = sanitize_html("<div>" * 5000 + "x", max_depth=10)
    assert deep.count("<div>") == 10 and deep.count("</div>") == 10 and "x" in deep
    assert 'colspan="100"' in sanitize_html('<table><tr><td colspan="99999">x</td></tr></table>')
    assert "colspan" not in sanitize_html('<td colspan="javascript:1">x</td>')


def test_rewrite_hooks_decide_images_and_links():
    out = sanitize_html(
        '<a href="http://a/">l</a><img src="k" alt="alt">',
        rewrite_href=lambda href: None,
        rewrite_src=lambda src: "data:" + src,
    )
    assert "href" not in out and 'src="data:k"' in out


def test_markdown_with_sanitize_ignores_scripts_and_unsafe_links():
    md = html_to_clean_markdown(
        "<p>hi <a href='javascript:x()'>there</a></p><script>x()</script>", sanitize=True
    )
    assert md == "hi there"


def test_lazy_package_names_still_resolve():
    import contaix

    assert contaix.html_to_clean_markdown is html_to_clean_markdown
    assert callable(contaix.verify_urls) and callable(contaix.bytes_to_markdown)
    assert "site_to_markdown" in dir(contaix)
