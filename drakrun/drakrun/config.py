import os
import json

from dataclasses import dataclass, asdict
from typing import Optional

ETC_DIR = os.getenv("DRAKRUN_ETC_DIR") or "/etc/drakrun"
LIB_DIR = os.getenv("DRAKRUN_LIB_DIR") or "/var/lib/drakrun"


@dataclass
class InstallInfo:
    storage_backend: str
    zfs_tank_name: Optional[str]
    disk_size: str
    iso_path: str
    max_vms: int
    enable_unattended: bool
    iso_sha256: Optional[str]

    def as_dict(self):
        return asdict(self)

    @staticmethod
    def load() -> 'InstallInfo':
        """ Reads and parses install.json file """
        with open(os.path.join(ETC_DIR, "install.json"), "r") as f:
            install_dict = json.loads(f.read())
            return InstallInfo(**install_dict)

    @classmethod
    def try_load(cls) -> Optional['InstallInfo']:
        """ Tries to load install.json of fails with None """
        try:
            return cls.load()
        except FileNotFoundError:
            return None

    def save(self):
        """ Serializes self and writes to install.json """
        with open(os.path.join(ETC_DIR, "install.json"), "w") as f:
            f.write(json.dumps(self.as_dict(), indent=4))


def is_installed() -> bool:
    """ Returns true when install.json is present """
    return InstallInfo.try_load() is not None
