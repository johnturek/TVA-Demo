"""
Shared exercise navigation menu for all Foundry labs.
Provides an interactive sub-menu for browsing exercise explanations.
"""

import inspect
import subprocess
from rich.console import Console
from rich.panel import Panel

console = Console()


def _open_in_editor(func):
    """Open the source file for *func* in VS Code at the function definition.

    Uses ``code -g file:line`` which works in Codespaces / vscode.dev terminals.
    Silently ignored when the ``code`` CLI is unavailable (local shell, SSH, etc.).
    """
    try:
        source_file = inspect.getfile(func)
        source_line = inspect.getsourcelines(func)[1]
        subprocess.Popen(
            ["code", "-g", f"{source_file}:{source_line}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def show_exercise_menu(lab_title: str, exercises: list[dict]):
    """Display an interactive exercise sub-menu.

    Parameters
    ----------
    lab_title : str
        Short lab title shown in the menu header (e.g. "Lab 01 — Prompts & Completions").
    exercises : list[dict]
        Each dict must have keys: num, title, short, why, concepts, builds_on.
    """
    while True:
        console.print()
        console.print(f"[bold cyan]{'═' * 64}[/]")
        console.print(f"[bold cyan]  {lab_title} — Exercise Navigator[/]")
        console.print(f"[bold cyan]{'═' * 64}[/]")
        for ex in exercises:
            console.print(f"  [bold]\\[{ex['num']}][/] {ex['title']}")
            console.print(f"      [dim]{ex['short']}[/]")
        console.print("  [bold]\\[A][/] View all explanations")
        console.print("  [bold]\\[Q][/] Back")
        console.print(f"[bold cyan]{'═' * 64}[/]")

        choice = console.input("\n[dim]Select an exercise: [/]").strip()

        if choice.lower() == "q":
            break

        if choice.lower() == "a":
            for ex in exercises:
                _show_exercise_explanation(ex)
            continue

        selected = next((ex for ex in exercises if ex["num"] == choice), None)
        if selected:
            _show_exercise_explanation(selected)
        else:
            console.print("[yellow]Invalid selection. Try again.[/]")


def show_exercise_intro(ex: dict, *, func=None):
    """Display an exercise explanation panel inline before the exercise runs.

    Call this right before each exercise function so the user sees the
    context, motivation, and key concepts before any output is generated.
    Pauses with "Press Enter to continue..." so the user can read the
    explanation before the exercise output begins.

    If *func* is supplied, the corresponding source file is opened in
    VS Code at the function definition (works in Codespaces / vscode.dev).
    """
    if func is not None:
        _open_in_editor(func)

    content = (
        f"[bold]{ex['title']}[/]\n\n"
        f"[bold yellow]Why This Matters[/]\n{ex['why']}\n\n"
        f"[bold yellow]Key Concepts[/]\n{ex['concepts']}\n\n"
        f"[bold yellow]Builds On[/]\n{ex['builds_on']}"
    )
    console.print(Panel(content, border_style="bright_magenta", padding=(1, 2)))
    console.input("[dim]Press Enter to continue...[/]")


def show_exercise_summary(ex: dict):
    """Display a summary panel after an exercise completes.

    Call this right after each exercise function returns so the user can
    review what they learned before moving on.  The exercise dict must
    include: summary, key_functions, code_pattern, and optionally
    looking_ahead.
    """
    parts = [
        f"[bold green]What You Did[/]\n{ex['summary']}\n",
        f"[bold green]New Functions & Concepts[/]\n{ex['key_functions']}\n",
        f"[bold green]Code Pattern to Remember[/]\n[cyan]{ex['code_pattern']}[/]",
    ]
    if ex.get("looking_ahead"):
        parts.append(f"\n[bold green]Looking Ahead[/]\n{ex['looking_ahead']}")

    content = "\n".join(parts)
    console.print(Panel(
        content,
        title=f"📝 {ex['title']} — Summary",
        border_style="dim green",
        padding=(1, 2),
    ))


def _show_exercise_explanation(ex: dict):
    """Render a detailed explanation panel for a single exercise."""
    content = (
        f"[bold]{ex['title']}[/]\n\n"
        f"[bold yellow]Why This Matters[/]\n{ex['why']}\n\n"
        f"[bold yellow]Key Concepts[/]\n{ex['concepts']}\n\n"
        f"[bold yellow]Builds On[/]\n{ex['builds_on']}"
    )
    console.print(Panel(content, border_style="bright_magenta", padding=(1, 2)))
    console.input("[dim]Press Enter to continue...[/]")
    show_exercise_summary(ex)
    console.input("[dim]Press Enter to continue...[/]")
