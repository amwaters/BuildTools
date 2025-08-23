from pathlib import Path
import re

from schema_build.base import BaseSchemaBuilder
from schema_build.typescript import TypeScriptBuilder
from schema_build.pgsql import PgsqlSchemaBuilder


def _parse_markdown_schema_and_fence(md_path: Path, fence_lang: str) -> tuple[str, str, list[str]]:
    text = md_path.read_text(encoding='utf-8')
    schema_match = re.search(r"```(yaml|json)\s*\n([\s\S]*?)\n```", text, re.MULTILINE)
    fence_match = re.search(rf"```{re.escape(fence_lang)}\s*\n([\s\S]*?)\n```", text, re.MULTILINE)
    if not schema_match:
        raise AssertionError(f"No schema code block found in {md_path.name}")
    expected_lines: list[str] = []
    if fence_match:
        fence_text = fence_match.group(1)
        expected_lines = [line.rstrip() for line in fence_text.splitlines() if line.strip()]
    schema_lang = schema_match.group(1)
    schema_text = schema_match.group(2) + "\n"
    return (schema_text, schema_lang, expected_lines)


def run_fixtures(builder_type: type[BaseSchemaBuilder], fence_lang: str, extension: str, monkeypatch) -> None:
    fixtures_dir = Path(__file__).parent
    out_dir = fixtures_dir.joinpath('.tests')
    out_dir.mkdir(parents=True, exist_ok=True)

    fixtures = sorted(list(fixtures_dir.glob('test_*.md')))
    assert fixtures, "No markdown fixture schemas found next to tests.py"

    monkeypatch.setattr(BaseSchemaBuilder, "validate", lambda self: None)

    tmp_dir = out_dir.joinpath('tmp')
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for md_path in fixtures:
        schema_text, schema_lang, expected_snippets = _parse_markdown_schema_and_fence(md_path, fence_lang)
        if not expected_snippets:
            continue
        schema_file = tmp_dir.joinpath(f"{md_path.stem}.{schema_lang}")
        schema_file.write_text(schema_text, encoding='utf-8')

        out_path = out_dir.joinpath(f"{md_path.stem}{extension}")
        builder = builder_type(schema_path=schema_file, output_path=out_path)
        builder.build()

        assert out_path.exists(), f"Expected output for {md_path.name} to be created"
        content = out_path.read_text(encoding='utf-8')
        assert content.strip(), f"Output for {md_path.name} is empty"
        for snippet in expected_snippets:
            assert snippet in content, f"Missing expected {fence_lang.upper()} snippet in {out_path.name}: {snippet}"


def test_typescript(monkeypatch) -> None:
    run_fixtures(TypeScriptBuilder, 'typescript', '.d.ts', monkeypatch)


def test_pgsql(monkeypatch) -> None:
    run_fixtures(PgsqlSchemaBuilder, 'sql', '.sql', monkeypatch)


