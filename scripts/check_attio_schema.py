import sys
from pathlib import Path
from typing import Annotated

import typer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from funda_app.schemas.crm import AttioSchemaPlan
from funda_app.services.attio_schema import (
    export_attio_schema,
    plan_attio_schema_changes,
)


def main(
    list_id: Annotated[
        str | None,
        typer.Option(help="Optional lifecycle list ID override."),
    ] = None,
    archive_extra_custom_attributes: Annotated[
        bool,
        typer.Option(help="Treat extra custom attributes as drift in the plan output."),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Print the schema plan as JSON."),
    ] = False,
) -> None:
    """
    Checks the current Attio schema against the canonical Funda schema.
    """
    snapshot = export_attio_schema(list_id=list_id)
    plan = plan_attio_schema_changes(
        snapshot=snapshot,
        archive_extra_custom_attributes=archive_extra_custom_attributes,
    )

    if as_json:
        typer.echo(plan.model_dump_json(indent=2))
    else:
        _print_plan(plan)

    raise typer.Exit(code=0 if plan.is_clean else 1)


def _print_plan(plan: AttioSchemaPlan) -> None:
    typer.echo(f"Lifecycle list ID: {plan.lifecycle_list_id or 'missing'}")
    if not plan.actions and not plan.issues:
        typer.echo("Schema is in sync.")
        return

    if plan.actions:
        typer.echo("Pending actions:")
        for action in plan.actions:
            label = action.api_slug or action.title or action.identifier
            typer.echo(
                f"- {action.kind}: {action.target}/{action.identifier} -> {label}"
            )

    if plan.issues:
        typer.echo("Blocking issues:")
        for issue in plan.issues:
            label = issue.api_slug or issue.identifier
            typer.echo(f"- {issue.kind}: {label} ({issue.message})")


if __name__ == "__main__":
    typer.run(main)
