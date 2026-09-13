"""Unit tests for Alembic migration chain integrity and offline SQL generation."""

import os
from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command


def get_alembic_config() -> Config:
    """Return configured Alembic Config object pointing to backend/alembic.ini."""
    backend_dir = Path(__file__).resolve().parents[2]
    ini_path = backend_dir / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    return cfg


def test_alembic_migration_chain_integrity():
    """Verify Alembic migration scripts form a single connected acyclic graph."""
    cfg = get_alembic_config()
    script = ScriptDirectory.from_config(cfg)
    
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected 1 head revision, got {heads}"
    assert heads[0] == "5a1b2c3d4e5f", f"Expected head 5a1b2c3d4e5f, got {heads[0]}"
    
    bases = script.get_bases()
    assert len(bases) == 1, f"Expected 1 base revision, got {bases}"
    assert bases[0] == "9766308ed13d", f"Expected base 9766308ed13d, got {bases[0]}"
    
    # Walk revisions from head to base
    revisions = list(script.walk_revisions())
    assert len(revisions) == 9, f"Expected 9 migration revisions, got {len(revisions)}"


def test_alembic_offline_sql_generation(capsys):
    """Verify offline SQL generation from base to head executes without syntax errors."""
    cfg = get_alembic_config()
    
    # Test upgrade head --sql
    command.upgrade(cfg, "head", sql=True)
    captured = capsys.readouterr()
    assert "CREATE TABLE announcements" in captured.out
    assert "CREATE TABLE academic_calendar" in captured.out
    assert "CREATE TABLE departments" in captured.out
    assert "CREATE TABLE faculty" in captured.out
    assert "CREATE TABLE people" in captured.out
    assert "UPDATE alembic_version SET version_num='5a1b2c3d4e5f'" in captured.out


def test_alembic_offline_downgrade_sql_generation(capsys):
    """Verify offline SQL generation for downgrade from head to base."""
    cfg = get_alembic_config()
    
    # Test downgrade head:base --sql
    command.downgrade(cfg, "head:base", sql=True)
    captured = capsys.readouterr()
    assert "DROP TABLE announcements" in captured.out
    assert "DROP TABLE academic_calendar" in captured.out
    assert "DELETE FROM alembic_version" in captured.out
