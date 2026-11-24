"""code_aggregate's folder walk (addaix/contaix#25): .gitignore, binaries, fences, packers."""

import os
import shutil
import subprocess

import pytest

from contaix.code import code_aggregate, fenced_item, packers, resolve_code_source


def _keys(store):
    """The store's keys with '/' separators, as on every platform."""
    return {k.replace(os.sep, "/") for k in store}


@pytest.fixture
def repo(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("build/\n*.log\n")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("x = 1\n")
    (tmp_path / "pkg" / "app.ts").write_text("export const y = 2;\n")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "gen.py").write_text("generated = True\n")
    (tmp_path / "debug.log").write_text("noise\n")
    (tmp_path / "logo.py").write_bytes(bytes([0x89, 0x50, 0x4E, 0x47, 0, 0, 1]))
    return tmp_path


def test_gitignored_and_binary_files_never_enter(repo):
    keys = _keys(resolve_code_source(str(repo), keys_filt=lambda k: True))
    assert {"pkg/mod.py", "pkg/app.ts"} <= keys
    assert not {"build/gen.py", "debug.log", "logo.py"} & keys


def test_the_old_walk_is_one_argument_away(repo):
    keys = _keys(
        resolve_code_source(
            str(repo), keys_filt=r"\.py$", respect_gitignore=False, skip_binary=False
        )
    )
    assert {"build/gen.py", "logo.py"} <= keys


def test_a_folder_outside_git_is_walked_as_before(tmp_path):
    (tmp_path / "a.py").write_text("a = 1\n")
    assert list(resolve_code_source(str(tmp_path))) == ["a.py"]


def test_each_file_is_fenced_in_its_language(repo):
    out = code_aggregate(str(repo), keys_filt=r"\.(py|ts)$", include_readme=None)
    out = out.replace(os.sep, "/") if os.sep != "/" else out
    assert "## pkg/mod.py\n\n```python\n" in out
    assert "## pkg/app.ts\n\n```typescript\n" in out


def test_a_markdown_file_with_its_own_fences_does_not_close_the_section():
    item = fenced_item("README.md", "Intro\n\n```python\nx = 1\n```\n\nMore")
    assert item.startswith("## README.md\n\n````markdown\n") and item.endswith("\n````")


def test_a_packer_replaces_the_walk_and_egress_still_applies(repo, tmp_path):
    seen = []

    def packer(folder):
        seen.append(folder)
        return "PACKED"

    assert code_aggregate(str(repo), packer=packer, egress=str.lower) == "packed"
    assert seen == [str(repo)]
    out_file = tmp_path / "out.md"
    assert code_aggregate(str(repo), packer=packer, egress=str(out_file)) == "PACKED"
    assert out_file.read_text() == "PACKED"


def test_repomix_without_node_says_how_to_get_it(repo, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="npx"):
        code_aggregate(str(repo), packer="repomix")


def test_repomix_runs_the_pinned_release_with_markdown_on_stdout(repo, monkeypatch):
    calls = []

    def fake_run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="# packed\n", stderr="")

    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/npx")
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert packers["repomix"](str(repo), compress=True) == "# packed\n"
    argv = calls[0]
    assert argv[2].startswith("repomix@") and "--stdout" in argv and "--compress" in argv


def test_a_packer_refuses_a_mapping():
    with pytest.raises(TypeError):
        code_aggregate({"a.py": "x"}, packer=lambda d: d)


def test_windows_keys_are_matched_against_gits_forward_slashes(repo, monkeypatch):
    import contaix.code as code

    keep = code._folder_filter(
        str(repo), lambda k: True, respect_gitignore=True, skip_binary=False
    )
    monkeypatch.setattr(code.os, "sep", "\\")
    assert keep("pkg\\mod.py") and not keep("build\\gen.py")


def test_a_folder_that_is_itself_ignored_is_walked_whole(repo):
    """The enclosing repo's rules say nothing inside an ignored folder (addaix/contaix#35)."""
    assert _keys(resolve_code_source(str(repo / "build"))) == {"gen.py"}
    # A package in an in-repo .venv: uv writes .venv/.gitignore = '*'.
    pkg = repo / ".venv" / "lib" / "site-packages" / "somepkg"
    pkg.mkdir(parents=True)
    (repo / ".venv" / ".gitignore").write_text("*\n")
    (pkg / "__init__.py").write_text("x = 1\n")
    (pkg / "core.py").write_text("y = 2\n")
    assert _keys(resolve_code_source(str(pkg))) == {"__init__.py", "core.py"}
    out = code_aggregate(str(pkg), include_readme=None)
    assert "## core.py" in out and "y = 2" in out
