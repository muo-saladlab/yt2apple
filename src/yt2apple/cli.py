import click
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from .apple_music import fetch_developer_token, get_user_token, search_song, create_playlist, _auth_headers
from .config import load_config, save_config
from .youtube import extract_tracks

console = Console()

@click.group()
def main():
    """Convert YouTube playlists to Apple Music playlists."""
    pass

VALID_STOREFRONTS = {"us", "kr", "jp", "gb"}

@main.command()
@click.argument("url")
@click.option("--name", "-n", default=None, help="Playlist name (defaults to YouTube title)")
@click.option("--storefront", "-s", default="kr", show_default=True, help="Apple Music storefront region code")
def convert(url: str, name: str | None, storefront: str) -> None:
    """Convert a YouTube playlist or video to an Apple Music playlist."""
    if storefront not in VALID_STOREFRONTS:
        console.print(f"[red]Invalid storefront '{storefront}'. Valid options: {', '.join(sorted(VALID_STOREFRONTS))}[/red]")
        return

    try:
        user_token = get_user_token()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        return

    console.print("\n[bold]Fetching YouTube data...[/bold]")
    try:
        playlist_name, tracks = extract_tracks(url)
    except Exception as e:
        console.print(f"[red]Failed to fetch YouTube data: {e}[/red]")
        return

    playlist_name = name or playlist_name
    console.print(f"[green]Found {len(tracks)} tracks in:[/green] [bold]{playlist_name}[/bold]\n")

    try:
        dev_token = fetch_developer_token()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        return

    matched: list[str] = []
    unmatched: list[str] = []
    uncertain_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Searching Apple Music...", total=len(tracks))
        for track in tracks:
            progress.update(task, description=f"Searching: [cyan]{track.search_query()[:50]}[/cyan]")
            song_id = search_song(track.title, track.artist, dev_token, user_token, storefront)
            if song_id:
                matched.append(song_id)
                if track.uncertain:
                    uncertain_count += 1
            else:
                unmatched.append(track.raw or track.search_query())
            progress.advance(task)

    console.print(f"\n[green]✓ Matched:[/green] {len(matched)} / {len(tracks)} songs")
    if uncertain_count:
        console.print(f"[yellow]  ↳ {uncertain_count} matched by title only (no artist info — may be wrong version)[/yellow]")

    if not matched:
        console.print("[red]No songs matched. Playlist not created.[/red]")
        return

    console.print(f"\n[bold]Creating Apple Music playlist:[/bold] {playlist_name}")
    playlist_id = create_playlist(playlist_name, matched, dev_token, user_token)

    if playlist_id:
        console.print("[bold green]✓ Playlist created successfully![/bold green]")
    else:
        console.print("[red]✗ Failed to create playlist. Check your token.[/red]")

    if unmatched:
        console.print(f"\n[yellow]Songs not found on Apple Music ({len(unmatched)}):[/yellow]")
        table = Table(show_header=False, box=None, padding=(0, 2))
        for song in unmatched:
            table.add_row(f"[dim]•[/dim]", song)
        console.print(table)

@main.command()
def setup():
    """Configure Apple Music authentication (media-user-token)."""
    console.print("\n[bold cyan]yt2apple Setup[/bold cyan]\n")
    console.print("You need to provide your Apple Music [bold]media-user-token[/bold] cookie.")
    console.print("This token is valid for ~180 days and does not require a developer account.\n")

    console.print("[bold]Steps to get your token:[/bold]")
    console.print("  1. Open [link=https://music.apple.com]https://music.apple.com[/link] in your browser")
    console.print("  2. Log in with your Apple ID")
    console.print("  3. Open DevTools (F12 or Cmd+Option+I)")
    console.print("  4. Go to [bold]Application[/bold] tab → [bold]Cookies[/bold] → music.apple.com")
    console.print("  5. Find the cookie named [bold yellow]media-user-token[/bold yellow]")
    console.print("  6. Copy its value and paste it below\n")

    token = click.prompt("Paste your media-user-token", hide_input=False)
    token = token.strip()

    if not token:
        console.print("[red]No token provided. Setup cancelled.[/red]")
        return

    config = load_config()
    config["media_user_token"] = token
    save_config(config)

    console.print("\n[dim]Validating token...[/dim]")
    try:
        dev_token = fetch_developer_token()
        headers = _auth_headers(dev_token, token)
        resp = requests.get(
            "https://amp-api.music.apple.com/v1/me/library/playlists",
            headers=headers,
            params={"limit": 1},
            timeout=10,
        )
        if resp.status_code == 200:
            console.print("[bold green]✓ Token valid! Apple Music connected.[/bold green]")
        elif resp.status_code == 401:
            console.print("[red]✗ Token invalid or expired. Please try again.[/red]")
        else:
            console.print(f"[yellow]Warning: Unexpected status {resp.status_code}. Token saved but may not work.[/yellow]")
    except Exception as e:
        console.print(f"[yellow]Could not validate token: {e}[/yellow]")
        console.print("[dim]Token saved. It will be validated when you run convert.[/dim]")
