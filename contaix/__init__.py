"""
Tools to make contexts (knowledge bases for AI agents)

Examples:

Download all articles from a markdown string and save them as PDF files:

>>> download_articles(md_string)  # doctest: +SKIP

Verify URLs in a markdown string by checking their status codes
(useful when trying to verify if AI hallucinated the urls)

>>> verify_urls(md_string)  # doctest: +SKIP

Make an md file with all the code in a directory:

>>> md_string = code_aggregate(package_or_folder_or_github_url)  # doctest: +SKIP

"""

# --------------------------------------------------------------------------------------
# General utilities

from contaix.util import (
    identity,
    fullpath,
    url_to_contents,
    save_to_file_and_return_file,
    remove_improperly_double_newlines,
)
from contaix.aggregation import aggregate_store
from contaix.code import (
    code_aggregate,  # get markdown aggregate of code from a directory, package, or GitHub URL
    PackageCodeContexts,
    prune_code_aggregate,  # strip bloat (node_modules, build output, ...) from an aggregate
    iter_pruned_aggregate_lines,  # streaming line-level pruner (memory-safe for huge files)
    DFLT_AGGREGATE_EXCLUDE_PATTERNS,  # default bloat patterns for aggregates
)


# Lazy re-exports. Two reasons to defer: names whose underlying packages (scraped,
# hubcap) raise at import time when GITHUB_TOKEN is unset, and heavy submodules
# (``contaix.markdown`` pulls notebook tooling, ~2 s) that a light consumer such as
# ``contaix.htmlmd`` should not pay for. ``from contaix import name`` still works:
# the owning submodule is imported on first use.
_LAZY = {
    "contaix.util": (
        "markdown_of_site",
        "download_site",
        "scrape_multiple_sites",
        "acquire_content",
    ),
    "contaix.code": ("get_github",),
    "contaix.urls": (
        "get_from_clipboard",
        "extract_urls",
        "verify_urls",
        "download_articles",
        "download_articles_by_section",
        "remove_hyperlink_crap",
    ),
    "contaix.markdown": (
        "bytes_to_markdown",
        "bytes_store_to_markdown_store",
        "dflt_converters",
        "add_dflt_converter",
        "truncate_text",
        "notebook_to_markdown",
    ),
    "contaix.web": (
        "site_to_markdown",
        "extract_site_nav",
        "list_site_pages",
        "fetch_page",
        "fetch_pages",
        "fetch_nextjs_rsc",
        "fetch_llms_full",
        "find_llms_full_url",
        "is_nextjs_site",
        "extract_rsc_page_content",
        "repair_markdown",
    ),
    "contaix.htmlmd": ("html_to_clean_markdown", "sanitize_html"),
}
_LAZY_OWNER = {name: mod for mod, names in _LAZY.items() for name in names}


def __getattr__(name):
    mod = _LAZY_OWNER.get(name)
    if mod is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    value = getattr(importlib.import_module(mod), name)
    globals()[name] = value  # cache: later lookups skip __getattr__
    return value


def __dir__():
    return sorted([*globals(), *_LAZY_OWNER])
