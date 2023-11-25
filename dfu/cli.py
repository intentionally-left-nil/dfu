import click

from dfu.commands.create_package import create_package
from dfu.commands.load_config import load_config


@click.group()
def main():
    pass


@main.command()
@click.option("-n", "--name", required=True, help="Name of the package")
def new(name: str):
    config = load_config()
    path = create_package(config, name)
    print(path)


if __name__ == "__main__":
    main()
