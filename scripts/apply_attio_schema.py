import sys
from pathlib import Path
from typing import Annotated

import typer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from funda_app.schemas.crm import AttioSchemaPlan
from funda_app.services.attio_schema import (
    apply_attio_schema_plan,
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
        typer.Option(
            help="Archive extra custom attributes that are not part of ATTIO_SCHEMA."
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(help="Print the planned changes without applying them."),
    ] = False,
) -> None:
    """
    Applies the canonical Funda Attio schema to the current workspace.
    """
    snapshot = export_attio_schema(list_id=list_id)
    plan = plan_attio_schema_changes(
        snapshot=snapshot,
        archive_extra_custom_attributes=archive_extra_custom_attributes,
    )

    _print_plan(plan)
    if plan.has_blockers:
        raise typer.Exit(code=1)

    if dry_run or plan.is_clean:
        raise typer.Exit(code=0)

    applied_snapshot = apply_attio_schema_plan(plan)
    lifecycle_list_id = (
        applied_snapshot.lifecycle_list.list_id
        if applied_snapshot.lifecycle_list is not None
        else "missing"
    )
    typer.echo(f"Applied schema. ATTIO_FOUNDER_LIFECYCLE_LIST_ID={lifecycle_list_id}")


def _print_plan(plan: AttioSchemaPlan) -> None:
    typer.echo(f"Lifecycle list ID: {plan.lifecycle_list_id or 'missing'}")
    if not plan.actions and not plan.issues:
        typer.echo("Schema is already in sync.")
        return

    if plan.actions:
        typer.echo("Actions:")
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
