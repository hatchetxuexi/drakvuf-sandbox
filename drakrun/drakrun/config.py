import os

from dataclasses import dataclass, asdict
from typing import Optional

ETC_DIR = "/etc/drakrun"
LIB_DIR = "/var/lib/drakrun"

@dataclass
class InstallInfo:
    storage_backend: str
    zfs_tank_name: Optional[str]
    disk_size: str
    iso_path: str
    max_vms: int
    enable_unattended: bool
    iso_sha256: str

    def as_dict(self):
        return asdict(self)

    @classmethod
    def load() -> Optional[InstallInfo]:
        try:
            with open(os.path.join(ETC_DIR, "install.json"), "r") as f:
                install_dict = json.loads(f.read())
                return InstallInfo(**install_dict)
        except FileNotFoundError:
            return None

    def save(self):
        with open(os.path.join(ETC_DIR, "install.json"), "w") as f:
            f.write(json.dumps(self.as_dict(), indent=4))

def is_installed() -> bool:
    return os.path.exists(os.path.join(ETC_DIR, "install.json"))
