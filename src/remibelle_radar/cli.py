import json

import typer

from .config import Settings
from .service import RadarService

app = typer.Typer(no_args_is_help=True)


@app.command()
def init_db() -> None:
    """Initialize the SQLite database."""
    service = RadarService(Settings())
    typer.echo(f"初期化完了: {service.settings.database_path}")


@app.command()
def run(no_sheets: bool = typer.Option(False, help="Skip Google Sheets sync")) -> None:
    """Run all three radars and always print a report."""
    results = RadarService(Settings()).run(sync_sheets=not no_sheets)
    for r in results:
        status = "成功" if r.failures == 0 else "一部失敗"
        typer.echo(f"[{status}] {r.radar.value}: 検索{r.searched}件 / 新規{r.added}件 / 重複{r.duplicates}件 / 対象外{r.excluded}件 / S級！！{r.s_count}件 / 失敗{r.failures}件")
        for error in r.errors:
            typer.echo(f"  エラー: {error}")
        if r.unpersisted:
            typer.echo(f"  更新できなかった候補: {', '.join(r.unpersisted)}")


@app.command()
def export_json() -> None:
    """Print current database contents for an operational audit."""
    service = RadarService(Settings())
    rows = service.db.rows("SELECT * FROM candidates ORDER BY id")
    typer.echo(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()

