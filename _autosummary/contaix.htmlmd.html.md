# contaix.htmlmd

Light html -> markdown: no web-scraping stack, optional sanitising for untrusted html.

`import contaix.htmlmd` costs only `scraped.html_markdown` (`markdownify` and
`bs4`): no pandas, numpy, requests or notebook tooling. [`contaix.web`](contaix.web.html.md#module-contaix.web) re-exports
[`html_to_clean_markdown()`](#contaix.htmlmd.html_to_clean_markdown), so existing imports keep working.

```pycon
>>> html_to_clean_markdown("<h1>Hi</h1><p>a <b>b</b></p>")
'# Hi\n\na **b**'
```

For html you do not trust, `sanitize=True` keeps only structure and words:

```pycon
>>> html_to_clean_markdown('<p onclick="x()">a</p><script>x()</script>', sanitize=True)
'a'
```

### Functions

| [`html_to_clean_markdown`](#contaix.htmlmd.html_to_clean_markdown)(html, \*[, ...])     | Convert HTML to clean markdown (via `markdownify`, MIT-licensed).                  |
|----------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| [`sanitize_html`](#contaix.htmlmd.sanitize_html)(text, \*[, rewrite_src, ...]) | The content of an html page as a safe fragment: structure and words, nothing live. |

### contaix.htmlmd.html_to_clean_markdown(html, , body_width=0, ignore_images=True, include_links=True, sanitize=False, \*\*markdownify_options)

Convert HTML to clean markdown (via `markdownify`, MIT-licensed).

A thin wrapper over `scraped.html_markdown.html_to_markdown_str()` (with the
`lxml` parser and no trailing newline), which owns the cleaning passes.

* **Parameters:**
  * **html** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Raw HTML content.
  * **body_width** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Kept for backward compatibility. Only `0` (no wrapping, the default)
    is supported; any other value raises `ValueError`.
  * **ignore_images** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to skip image tags.
  * **include_links** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to include hyperlinks in output (`False` keeps the link text only).
  * **sanitize** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Pass the html through [`sanitize_html()`](#contaix.htmlmd.sanitize_html) first: use it for untrusted html.
    Remote images become their alt text, and only `http(s)`/`mailto` links stay.
  * **\*\*markdownify_options** – Options for `markdownify.MarkdownConverter`, overriding
    `HTML_TO_MARKDOWN_DEFAULTS`. Unknown names raise `TypeError`
    (`MarkdownConverter` would silently ignore them), in particular the
    `html2text` options this function accepted before (`ignore_links`,
    `unicode_snob`, …).
  * **href='u'>c</a></p>"****)** ( *>>> html_to_clean_markdown* *(* *"<h1>Hi</h1><p>a <b>b</b> <a*)
  * **[****c****]****(****u****)****'** ( *'# Hinna b*)
  * **href='u'>c</a></p>"** ( *>>> html_to_clean_markdown* *(* *"<p>a <a*)
  * **include_links=False****)**
  * **c'** ( *'a*)
  * **href='javascript** ( *>>> html_to_clean_markdown* *(* *"<p>a <a*)
  * **c'**
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### contaix.htmlmd.sanitize_html(text, \*, rewrite_src=<function <lambda>>, rewrite_href=None, max_depth=100, max_span=100)

The content of an html page as a safe fragment: structure and words, nothing live.

Only `ALLOWED_TAGS` survive, with a few plain attributes (`KEEP_ATTRS`):
no script, style, frame, form, event handler, `class` or `id`. A link keeps only an
`http(s)` or `mailto` address, which `rewrite_href(href)`, when given, may change
or refuse (`None`: the link keeps its words and loses its address).
`rewrite_src(src)` decides each image: the url to show it from, or `None` for its alt
text instead (by default every remote image becomes its alt text). Nesting deeper than
`max_depth` is unwrapped, spans are capped at `max_span`, and unbalanced tags are
closed so the fragment can never swallow what is joined after it.

```pycon
>>> sanitize_html('<body><script>x()</script><h1 onclick="x()">Hi</h1><a href="javascript:x()">y</a></body>')
'<h1>Hi</h1><a>y</a>'
>>> sanitize_html("<div><p>unclosed")
'<div><p>unclosed</p></div>'
>>> sanitize_html('<img src="http://e/x.png" alt="a cat">')
'a cat'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
