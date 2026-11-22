"""Light html -> markdown: no web-scraping stack, optional sanitising for untrusted html.

``import contaix.htmlmd`` costs only ``scraped.html_markdown`` (``markdownify`` and
``bs4``): no pandas, numpy, requests or notebook tooling. :mod:`contaix.web` re-exports
:func:`html_to_clean_markdown`, so existing imports keep working.

>>> html_to_clean_markdown("<h1>Hi</h1><p>a <b>b</b></p>")
'# Hi\\n\\na **b**'

For html you do not trust, ``sanitize=True`` keeps only structure and words:

>>> html_to_clean_markdown('<p onclick="x()">a</p><script>x()</script>', sanitize=True)
'a'
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from html.parser import HTMLParser
from urllib.parse import urlsplit

from scraped.html_markdown import HTML_TO_MARKDOWN_DEFAULTS, html_to_markdown_str

__all__ = ["html_to_clean_markdown", "sanitize_html"]

#: nesting depth beyond which tags are unwrapped (their content stays)
DFLT_MAX_DEPTH = 100
#: ceiling for ``colspan`` / ``rowspan``
DFLT_MAX_SPAN = 100

ALLOWED_TAGS = frozenset(
    "a abbr article aside b blockquote br caption cite code dd del details div dl dt em "
    "figcaption figure footer h1 h2 h3 h4 h5 h6 header hr i img ins kbd li main mark nav "
    "ol p pre q s section small span strong sub summary sup table tbody td tfoot th thead "
    "time tr u ul".split()
)
VOID_TAGS = frozenset(
    "br hr img embed frame input source track wbr area col link meta base param".split()
)
#: elements dropped together with everything inside them
DROPPED_TAGS = frozenset(
    "script style head title noscript template iframe object embed svg math "
    "canvas audio video applet frame frameset".split()
)
SAFE_LINK_SCHEMES = ("http", "https", "mailto")
KEEP_ATTRS = {
    "a": ("href", "title"),
    "img": ("alt", "title"),
    "td": ("colspan", "rowspan"),
    "th": ("colspan", "rowspan"),
}


def _safe_link(value: str | None) -> bool:
    return bool(value) and urlsplit(value.strip()).scheme in SAFE_LINK_SCHEMES


def sanitize_html(
    text: str,
    *,
    rewrite_src: Callable[[str], str | None] = lambda src: None,
    rewrite_href: Callable[[str], str | None] | None = None,
    max_depth: int = DFLT_MAX_DEPTH,
    max_span: int = DFLT_MAX_SPAN,
) -> str:
    """The content of an html page as a safe fragment: structure and words, nothing live.

    Only :data:`ALLOWED_TAGS` survive, with a few plain attributes (:data:`KEEP_ATTRS`):
    no script, style, frame, form, event handler, ``class`` or ``id``. A link keeps only an
    ``http(s)`` or ``mailto`` address, which ``rewrite_href(href)``, when given, may change
    or refuse (``None``: the link keeps its words and loses its address).
    ``rewrite_src(src)`` decides each image: the url to show it from, or ``None`` for its alt
    text instead (by default every remote image becomes its alt text). Nesting deeper than
    ``max_depth`` is unwrapped, spans are capped at ``max_span``, and unbalanced tags are
    closed so the fragment can never swallow what is joined after it.

    >>> sanitize_html('<body><script>x()</script><h1 onclick="x()">Hi</h1><a href="javascript:x()">y</a></body>')
    '<h1>Hi</h1><a>y</a>'
    >>> sanitize_html("<div><p>unclosed")
    '<div><p>unclosed</p></div>'
    >>> sanitize_html('<img src="http://e/x.png" alt="a cat">')
    'a cat'
    """
    out: list[str] = []
    open_tags: list[str] = []
    skip: list[str] = []  # the dropped elements we are inside

    class Cleaner(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "body" and skip and skip[0] in ("head", "title"):
                skip.clear()  # </head> or </title> was left out: the body starts here
            if skip:
                if tag == skip[-1]:
                    skip.append(tag)
                return
            if tag in DROPPED_TAGS:
                if tag not in VOID_TAGS:
                    skip.append(tag)
                return
            if tag not in ALLOWED_TAGS or len(open_tags) >= max_depth:
                return  # unwrapped: its content stays
            kept = dict(attrs)
            parts = [tag]
            for attr in KEEP_ATTRS.get(tag, ()):
                value = kept.get(attr)
                if attr == "href":
                    if not _safe_link(value):
                        continue
                    if rewrite_href is not None:
                        value = rewrite_href(value)
                        if not _safe_link(value):
                            continue
                if attr in ("colspan", "rowspan"):
                    if not (value or "").strip().isdigit():
                        continue
                    value = str(min(int(value.strip()), max_span))
                if value is not None:
                    parts.append(f'{attr}="{html.escape(value, quote=True)}"')
            if tag == "img":
                shown = rewrite_src(kept.get("src") or "")
                if shown is None:
                    out.append(html.escape(kept.get("alt") or ""))
                    return
                parts.append(f'src="{html.escape(shown, quote=True)}"')
            out.append(f"<{' '.join(parts)}>")
            if tag not in VOID_TAGS:
                open_tags.append(tag)

        def handle_endtag(self, tag):
            if skip:
                if tag == skip[-1]:
                    skip.pop()
                return
            if tag in ALLOWED_TAGS and tag not in VOID_TAGS and tag in open_tags:
                while open_tags:
                    top = open_tags.pop()
                    out.append(f"</{top}>")
                    if top == tag:
                        break

        def handle_data(self, data):
            if not skip:
                out.append(html.escape(data, quote=False))

        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
            if tag not in VOID_TAGS:
                self.handle_endtag(tag)

    cleaner = Cleaner(convert_charrefs=True)
    cleaner.feed(text)
    cleaner.close()
    while open_tags:
        out.append(f"</{open_tags.pop()}>")
    return "".join(out).strip()


def html_to_clean_markdown(
    html: str,
    *,
    body_width: int = 0,
    ignore_images: bool = True,
    include_links: bool = True,
    sanitize: bool = False,
    **markdownify_options,
) -> str:
    """Convert HTML to clean markdown (via ``markdownify``, MIT-licensed).

    A thin wrapper over :func:`scraped.html_markdown.html_to_markdown_str` (with the
    ``lxml`` parser and no trailing newline), which owns the cleaning passes.

    Parameters
    ----------
    html : str
        Raw HTML content.
    body_width : int
        Kept for backward compatibility. Only ``0`` (no wrapping, the default)
        is supported; any other value raises ``ValueError``.
    ignore_images : bool
        Whether to skip image tags.
    include_links : bool
        Whether to include hyperlinks in output (``False`` keeps the link text only).
    sanitize : bool
        Pass the html through :func:`sanitize_html` first: use it for untrusted html.
        Remote images become their alt text, and only ``http(s)``/``mailto`` links stay.
    **markdownify_options
        Options for ``markdownify.MarkdownConverter``, overriding
        :data:`HTML_TO_MARKDOWN_DEFAULTS`. Unknown names raise ``TypeError``
        (``MarkdownConverter`` would silently ignore them), in particular the
        ``html2text`` options this function accepted before (``ignore_links``,
        ``unicode_snob``, ...).

    >>> html_to_clean_markdown("<h1>Hi</h1><p>a <b>b</b> <a href='u'>c</a></p>")
    '# Hi\\n\\na **b** [c](u)'
    >>> html_to_clean_markdown("<p>a <a href='u'>c</a></p>", include_links=False)
    'a c'
    >>> html_to_clean_markdown("<p>a <a href='javascript:x()'>c</a></p>", sanitize=True)
    'a c'
    """
    if body_width:
        raise ValueError(
            "body_width is not supported: markdownify never wraps lines. "
            "Pass body_width=0 (the default)."
        )
    if sanitize:
        html = sanitize_html(html)
    return html_to_markdown_str(
        html,
        ignore_images=ignore_images,
        include_links=include_links,
        parser="lxml",
        **markdownify_options,
    ).strip()
