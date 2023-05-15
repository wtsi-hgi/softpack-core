"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import typer

app = typer.Typer()


@app.command()
def hello(name: str):
    """Handle CLI command 'hello'."""
    typer.echo(f"Hello {name}")


@app.command()
def goodbye(name: str, formal: bool = False):
    """Handle CLI command 'goodbye'."""
    if formal:
        typer.echo(f"Goodbye {name}. Have a good day.")
    else:
        typer.echo(f"Bye {name}!")


def main():
    """Main entrypoint."""
    app()


if __name__ == "__main__":
    main()  # pragma: no cover
