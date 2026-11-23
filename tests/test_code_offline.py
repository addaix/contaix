"""contaix.code pure helpers (addaix/contaix#31): pruning, exclusion predicates, section detection, fences."""

import pytest

from contaix.code import (
    _exclude_predicate,
    _looks_like_section_path,
    fence_language,
    fenced_item,
    is_local_pkg_name,
    iter_pruned_aggregate_lines,
    prune_code_aggregate,
)

AGG = "\n\n".join(
    [
        "## pkg/mod.py\n\n```python\nx = 1\n```",
        "## node_modules/lib/index.js\n\n```javascript\nvar a;\n```\n",
        "## pkg/README.md\n\n````markdown\n## Overview\n```\nstray\n```\n````",
    ]
)


def test_is_local_pkg_name():
    assert is_local_pkg_name("os")
    assert not is_local_pkg_name("definitely_not_a_module_xyz")


@pytest.mark.parametrize(
    "exclude,path,dropped",
    [
        (None, "a.py", False),
        ("^vendor/", "vendor/x.py", True),
        (["\\.lock$", "^dist/"], "dist/a.js", True),
        (["\\.lock$"], "a.py", False),
        (lambda p: p.endswith(".js"), "a.js", True),
    ],
)
def test_exclude_predicate(exclude, path, dropped):
    assert _exclude_predicate(exclude)(path) is dropped


@pytest.mark.parametrize(
    "path,expected",
    [("pkg/mod.py", True), ("setup.py", True), ("Overview", False), ("Some heading text", False)],
)
def test_looks_like_section_path(path, expected):
    assert _looks_like_section_path(path) is expected


def test_prune_drops_excluded_section_only():
    dropped = []
    out = prune_code_aggregate(AGG, exclude=["^node_modules/"], on_drop=dropped.append)
    assert "node_modules" not in out and "var a" not in out
    assert "x = 1" in out
    assert dropped and "node_modules" in dropped[0]


def test_prune_keeps_stray_fences_and_in_content_headings():
    out = prune_code_aggregate(AGG, exclude=["^node_modules/"])
    assert "## Overview" in out and "stray" in out


def test_prune_no_exclusion_is_identity():
    out = "".join(iter_pruned_aggregate_lines(AGG.splitlines(keepends=True), exclude=None))
    assert out == AGG


def test_prune_writes_to_filepath(tmp_path):
    target = tmp_path / "out.md"
    prune_code_aggregate(AGG, exclude=["^node_modules/"], egress=str(target))
    assert "x = 1" in target.read_text() and "var a" not in target.read_text()


def test_fence_language_and_fenced_item_longer_fence():
    assert fence_language("a/b.py") == "python"
    assert fence_language("LICENSE") == ""
    item = fenced_item("doc.md", "```py\nx\n```")
    assert item.splitlines()[2].startswith("````")
