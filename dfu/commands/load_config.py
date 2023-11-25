from dfu.config import Config


def load_config() -> Config:
    return Config.from_file("/etc/dfu/config.toml")
