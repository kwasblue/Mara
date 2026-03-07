# mara_host/cli/console.py
"""Rich console helpers for MARA CLI."""

from contextlib import contextmanager
from typing import Any, Generator, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# Custom theme for MARA
MARA_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "muted": "dim",
    "highlight": "bold magenta",
    "pin.assigned": "green",
    "pin.available": "cyan",
    "pin.boot": "yellow",
    "pin.flash": "red",
    "pin.input_only": "blue",
})

# Global console instance
console = Console(theme=MARA_THEME)


def print_header(title: str, subtitle: str = "") -> None:
    """Print a styled section header."""
    text = Text(title, style="bold cyan")
    if subtitle:
        text.append(f"\n{subtitle}", style="dim")
    console.print(Panel(text, border_style="blue", padding=(0, 2)))


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[success]\u2713[/success] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[error]\u2717[/error] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]\u26a0[/warning]  {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[info]\u2139[/info]  {message}")


def print_table(
    title: str,
    columns: list[tuple[str, str]],
    rows: list[list[Any]],
    show_header: bool = True,
) -> None:
    """Print a formatted table.

    Args:
        title: Table title
        columns: List of (header, style) tuples
        rows: List of row data lists
        show_header: Whether to show column headers
    """
    table = Table(title=title, show_header=show_header)

    for header, style in columns:
        table.add_column(header, style=style)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    console.print(table)


def create_pin_table(title: str = "") -> Table:
    """Create a table configured for pin display."""
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("GPIO", style="cyan", justify="right", width=5)
    table.add_column("Status", style="white", width=18)
    table.add_column("Capabilities", style="dim", width=24)
    table.add_column("Notes", style="white")
    return table


@contextmanager
def spinner(message: str) -> Generator[None, None, None]:
    """Show a spinner for long-running operations."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description=message, total=None)
        yield


def print_pinout_panel(pinout_text: str, title: str = "ESP32 DevKit V1") -> None:
    """Print the pinout diagram in a styled panel with color coding."""
    # Apply rich markup to the pinout
    styled = pinout_text

    # Color the legend markers
    styled = styled.replace("# = assigned", "[green]#[/green] = assigned")
    styled = styled.replace("o = available", "[cyan]o[/cyan] = available")
    styled = styled.replace("! = boot", "[yellow]![/yellow] = boot")
    styled = styled.replace("> = input only", "[blue]>[/blue] = input only")
    styled = styled.replace("x = flash", "[red]x[/red] = flash")
    styled = styled.replace("= = power/ground", "[white]=[/white] = power/ground")

    console.print(Panel(
        styled,
        title=f"[bold cyan]{title}[/bold cyan]",
        border_style="blue",
        padding=(0, 1),
    ))


def format_pin_status(
    gpio: int,
    assigned_name: Optional[str],
    is_flash: bool,
    is_boot: bool,
    is_input_only: bool,
    has_warning: bool,
) -> tuple[str, str]:
    """Format pin status with styling.

    Returns:
        Tuple of (status_text, style)
    """
    if assigned_name:
        return f"[{assigned_name}]", "green"
    elif is_flash:
        return "(FLASH - unusable)", "red"
    elif is_boot and has_warning:
        return "(boot - caution)", "yellow"
    elif is_input_only:
        return "(input only)", "blue"
    elif has_warning:
        return "(caution)", "yellow"
    else:
        return "available", "cyan"


def confirm(message: str, default: bool = False) -> bool:
    """Ask for user confirmation."""
    suffix = " [Y/n]" if default else " [y/N]"
    response = console.input(f"[yellow]?[/yellow] {message}{suffix} ")
    if not response:
        return default
    return response.lower() in ("y", "yes")
