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
    
def reload_install_info():
    global install_info
    try:
        with open(os.path.join(ETC_DIR, "install.json"), "rb") as f:
            install_dict = json.loads(f.read())
            install_info = InstallInfo(**install_dict)
    except FileNotFoundError:
        install_info = None

reload_install_info()
