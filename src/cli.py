"""Command-line interface for yt-transcript-filter."""

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from .fetcher import get_video_list, fetch_all_transcripts
from .storage import save_transcripts
from .filter import keyword_search, filter_by_topic

console = Console()


@click.group()
def cli():
    """YouTube Transcript Filter — scrape, save, and search video transcripts."""
    pass


@cli.command()
@click.argument("url")
@click.option("--output", "-o", default="./transcripts", help="Output directory for transcripts.")
@click.option("--lang", "-l", default="en", help="Transcript language (default: en).")
def fetch(url: str, output: str, lang: str):
    """Fetch transcripts from a YouTube channel or playlist URL."""
    languages = [l.strip() for l in lang.split(",")]

    console.print(f"\n[bold blue]🔍 Fetching video list from:[/] {url}\n")

    with console.status("Getting video list..."):
        videos = get_video_list(url)

    console.print(f"[green]Found {len(videos)} videos.[/]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching transcripts...", total=len(videos))

        def on_progress(current, total, video):
            status = "✅" if video.transcript else "❌"
            progress.update(task, completed=current, description=f"{status} {video.title[:50]}")

        fetch_all_transcripts(videos, languages=languages, progress_callback=on_progress)

    # Summary
    with_transcript = sum(1 for v in videos if v.transcript)
    console.print(f"\n[green]✅ {with_transcript}/{len(videos)} videos have transcripts.[/]")

    save_path = save_transcripts(videos, output)
    console.print(f"[bold]📁 Saved to: {save_path}[/]\n")


@cli.command()
@click.argument("keywords", nargs=-1, required=True)
@click.option("--dir", "-d", "transcript_dir", default="./transcripts", help="Transcripts directory.")
def search(keywords: tuple, transcript_dir: str):
    """Search transcripts for keywords."""
    console.print(f"\n[bold blue]🔎 Searching for:[/] {', '.join(keywords)}\n")

    results = keyword_search(transcript_dir, list(keywords))

    if not results:
        console.print("[yellow]No matches found.[/]")
        return

    table = Table(title=f"Found {len(results)} matching videos")
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Matches", style="green", justify="right")
    table.add_column("URL", style="blue")

    for r in results:
        table.add_row(r.title, str(r.matches), r.url)

    console.print(table)

    # Show snippets for top results
    for r in results[:3]:
        console.print(f"\n[bold cyan]{r.title}[/]")
        for snippet in r.snippets[:2]:
            console.print(f"  [dim]{snippet}[/]")


@cli.command()
@click.option("--dir", "-d", "transcript_dir", default="./transcripts", help="Transcripts directory.")
@click.option("--include", "-i", multiple=True, help="Include videos mentioning these keywords.")
@click.option("--exclude", "-e", multiple=True, help="Exclude videos mentioning these keywords.")
def filter(transcript_dir: str, include: tuple, exclude: tuple):
    """Filter videos by topic keywords (include/exclude)."""
    if not include and not exclude:
        console.print("[red]Provide at least --include or --exclude keywords.[/]")
        return

    console.print(f"\n[bold blue]🏷️  Filtering videos[/]")
    if include:
        console.print(f"  [green]Include:[/] {', '.join(include)}")
    if exclude:
        console.print(f"  [red]Exclude:[/] {', '.join(exclude)}")
    console.print()

    results = filter_by_topic(
        transcript_dir,
        include_keywords=list(include) if include else None,
        exclude_keywords=list(exclude) if exclude else None,
    )

    if not results:
        console.print("[yellow]No videos match the filter criteria.[/]")
        return

    table = Table(title=f"{len(results)} videos match")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Title", style="cyan", max_width=60)
    table.add_column("URL", style="blue")

    for i, entry in enumerate(results, 1):
        url = f"https://www.youtube.com/watch?v={entry['video_id']}"
        table.add_row(str(i), entry["title"], url)

    console.print(table)


def main():
    cli()


if __name__ == "__main__":
    main()
