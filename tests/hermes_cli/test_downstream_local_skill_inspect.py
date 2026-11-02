"""Exercise installed-skill preview with real skill discovery and no network."""
from io import StringIO

from rich.console import Console


def test_installed_skill_inspect_uses_local_content(tmp_path, monkeypatch):
    import tools.skills_tool as skills
    from hermes_cli import skills_hub

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(skills, "SKILLS_DIR", tmp_path / "skills")
    skill_dir = tmp_path / "skills" / "downstream-preview-check"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: downstream-preview-check\ndescription: Local preview regression\n---\n"
        "# Local preview\nContent from installed skill.\n"
    )

    def no_remote_sources():
        raise AssertionError("installed preview must not consult remote sources")

    monkeypatch.setattr(skills_hub, "_sources", no_remote_sources)
    preview = skills_hub.inspect_skill("downstream-preview-check")
    assert preview is not None
    assert preview["source"] == "installed"
    assert "Content from installed skill." in preview["skill_md_preview"]
    output = StringIO()
    skills_hub.do_inspect("downstream-preview-check", Console(file=output, width=120))
    assert "Content from installed skill." in output.getvalue()
