import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from funda_app.services.attio_schema import export_attio_schema


def main(
    list_id: Annotated[
        str | None,
        typer.Option(help="Optional lifecycle list ID override."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(help="Optional output path for the JSON snapshot."),
    ] = None,
) -> None:
    """
    Exports the current Attio schema snapshot to disk.
    """
    snapshot = export_attio_schema(list_id=list_id)
    output_path = output or _default_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(output_path)


def _default_output_path() -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path("outputs/attio_schema") / f"attio_schema_{timestamp}.json"


if __name__ == "__main__":
    typer.run(main)
