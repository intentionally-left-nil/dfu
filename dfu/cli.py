import click

from dfu.commands.create_package import create_package
from dfu.commands.load_config import load_config


class NullableString(click.ParamType):
    name = "string"

    def convert(self, value, param, ctx):
        if value == "":
            return None
        return value


@click.group()
def main():
    pass


@main.command()
@click.option("-n", "--name", help="Name of the package")
@click.option("-d", "--description", help="Description of the package")
def new(name: str | None, description: str | None):
    final_name: str = click.prompt("Name", default=name)
    final_description: str | None = click.prompt("Description", default=description or "", type=NullableString())
    config = load_config()
    path = create_package(config, name=final_name, description=final_description)
    print(path)


if __name__ == "__main__":
    main()
