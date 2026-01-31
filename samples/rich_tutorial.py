import time
from rich.console import Console
from rich.theme import Theme
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.columns import Columns

console = Console()
console.print("[bold magenta]Hello, World![/bold magenta]")
console.print("[green]This is a sample application using the Rich library for colorful terminal output.[/green]")
console.print("[yellow]Enjoy coding with style![/yellow]")
console.print({"apple": 1, "banana": 2, "cherry": 3})
console.print("[blue]Goodbye![/blue]")

console.print("This is some text.")
console.print("This is some text.", style="bold")
console.print("This is some text.", style="bold underline")
console.print("This is some text.", style="bold underline red")
console.print("This is some text.", style="bold underline red on black")
console.print("[bold]This [underline]is[/] some text.[/]")

custom_theme = Theme({
    "good" : "green",
    "bad": "bold red"
})

console = Console(theme=custom_theme)
console.print("File downloaded!", style="good")
console.print("File corrupted!", style="bad")
console.print("The internet is [bad]down![/bad]")
console.print(":thumbs_up: File downloaded!")
for i in range(10):
    console.log(f"I am about to sleep={i}")
    time.sleep(0.2)
    console.log("But I am briefly awake now.")


console = Console(record=True, width=100)

tree = Tree("🙂 [link=https://koaning.io]Vincent D. Warmerdam", guide_style="bold bright_black")

python_tree = tree.add("📦 Open Source Packages", guide_style="bright_black")
python_tree.add("[bold link=https://scikit-lego.netlify.app/]scikit-lego[/] - [bright_black]lego bricks for sklearn")
python_tree.add("[bold link=https://koaning.github.io/human-learn/]human-learn[/] - [bright_black]rule-based components for sklearn")

online_tree = tree.add("⭐ Online Projects", guide_style="bright_black")
online_tree.add("[bold link=https://koaning.io]koaning.io[/]   - [bright_black]personal blog")
online_tree.add("[bold link=https://calmcode.io]calmcode.io[/]  - [bright_black]dev education service")

talk_tree = tree.add("🎙️ Popular Talks", guide_style="bright_black")
talk_tree.add("[bold link=https://youtu.be/qcrR-Hd0LhI?t=542]Optimal Benchmarks and Other Failures[/]")
talk_tree.add("[bold link=https://www.youtube.com/watch?v=nJAmN6gWdK8]Playing by the Rules-Based-Systems[/]")

employer_tree = tree.add("👨‍💻 Employer", guide_style="bright_black")
employer_tree.add("[bold link=https://rasa.com]Rasa[/] - [bright_black]conversational software")

console.print(tree)
console.print("")
console.print("[green]Follow me on twitter [bold link=https://twitter.com/fishnets88]@fishnets88[/]")


table = Table(title="Pandas Versions")

table.add_column("Released", style="cyan")
table.add_column("Version Number", justify="right", style="magenta")
table.add_column("Description", style="green")

table.add_row("May 29, 2020", "v1.0.4", "Just an update.")
table.add_row("Mar 18, 2020", "v1.0.3", "Just an update.")
table.add_row("Mar 15, 2020", "v1.0.2", "Just an update.")
table.add_row("Feb 05, 2020", "v1.0.1", ":thumbs_up: [underline]Big[/] update.")

console = Console()
console.print(table)


md1 = """
# Hello World

## This is Markdown

And it renders *very* **nicely**!
"""

md2 = """
## This is Markdown, Again

With code!

```python
print("hello world")
```
"""

console = Console(record=True)
panel_1 = Panel.fit(Markdown(md1), title="panel one", width=60)
panel_2 = Panel.fit(Markdown(md2), title="panel two", width=60)
console.print(Columns([panel_1, panel_2]))



def add_two(n1: int, n2: int) -> int:
    console.log("About to add two numbers.", log_locals=True)
    return n1 + n2

try:
    console = Console(record=True)
    for i in range(10):
        time.sleep(0.2)
        add_two(1, i)
    add_two(1, 'a') # type: ignore
except:  # noqa: E722
    console.print_exception()
