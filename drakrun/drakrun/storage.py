import logging
import subprocess
import shlex

from typing import Any


class StorageBackendBase:
    """Base class for all storage backends

    Defines interface that has to be implemented in order to be
    considered a valid storage backend for DRAKVUF sandbox.

    In DRAKVUF Sandbox, worker virtual machines are named from
    vm-1 to vm-[n] - as configured by max_vms parameter during setup.

    vm-0 is considered special as it is used as a base for running
    other machines. The steps from creating vm-0 to running a worker are:
    create vm-0 -> configure vm-0 -> snapshot vm-0 -> restore vm-0 as vm-[i]
    """

    def __init__(self, install_info: Dict[str, Any]):
        self._install_info = install_info

    def initialize_vm0_volume(self, disk_size: str):
        """Create base volume for VM-0 with given size

        disk_size - string representing volume size with M/G/T suffix, eg. 100G
        """
        raise NotImplementedError

    def snapshot_vm0_volume(self):
        """ Save or snapshot base VM-0 volume for later use by other VMs """
        raise NotImplementedError

    def get_vm_disk_path(self, vm_id: int) -> str:
        """ Returns disk path for given VM as defined by XL configuration """
        raise NotImplementedError

    def rollback_vm_storage(self, vm_id: int):
        """ Rolls back changes and prepares fresh storage for new run of this VM """
        raise NotImplementedError


class ZfsStorageBackend(StorageBackendBase):
    def __init__(self):
        self.check_tools()

    def check_tools(self):
        try:
            subprocess.check_output("zfs -?", shell=True)
        except subprocess.CalledProcessError:
            logging.exception(
                "Failed to execute zfs command. Make sure you have ZFS support installed."
            )
            return

    def initialize_vm0_volume(self, disk_size):
        vm0_vol = shlex.quote(os.path.join(zfs_tank_name, "vm-0"))
        try:
            subprocess.check_output(
                f"zfs destroy -Rfr {vm0_vol}", stderr=subprocess.STDOUT, shell=True
            )
        except subprocess.CalledProcessError as e:
            if b"dataset does not exist" not in e.output:
                logging.exception(
                    f"Failed to destroy the existing ZFS volume {vm0_vol}."
                )
        try:
            subprocess.check_output(
                " ".join(
                    [
                        "zfs",
                        "create",
                        "-V",
                        shlex.quote(disk_size),
                        shlex.quote(os.path.join(zfs_tank_name, "vm-0")),
                    ]
                ),
                shell=True,
            )
        except subprocess.CalledProcessError:
            logging.exception("Failed to create a new volume using zfs create.")
            return

    def snapshot_vm0_volume(self):
        snap_name = shlex.quote(
            os.path.join(install_info["zfs_tank_name"], "vm-0@booted")
        )
        subprocess.check_output(f"zfs snapshot {snap_name}", shell=True)

    def get_vm_disk_path(self, vm_id: int) -> str:
        zfs_tank_name = self._install_info["zfs_tank_name"]
        return f"phy:/dev/zvol/{zfs_tank_name}/vm-{vm_id},hda,w"

    def rollback_vm_storage(self, vm_id: int):
        vm_zvol = os.path.join(
            "/dev/zvol", install_info["zfs_tank_name"], f"vm-{vm_id}"
        )
        vm_snap = os.path.join(install_info["zfs_tank_name"], f"vm-{vm_id}@booted")

        if not os.path.exists(vm_zvol):
            subprocess.run(
                [
                    "zfs",
                    "clone",
                    "-p",
                    os.path.join(install_info["zfs_tank_name"], "vm-0@booted"),
                    os.path.join(install_info["zfs_tank_name"], f"vm-{vm_id}"),
                ],
                check=True,
            )

            for _ in range(120):
                if not os.path.exists(vm_zvol):
                    time.sleep(0.1)
                else:
                    break
            else:
                logging.error(
                    f"Failed to see {vm_zvol} created after executing zfs clone command."
                )
                return

            subprocess.run(["zfs", "snapshot", vm_snap], check=True)

        subprocess.run(["zfs", "rollback", vm_snap], check=True)


class Qcow2StorageBackend(StorageBackendBase):
    def __init__(self):
        self.check_tools()

    def check_tools(self):
        try:
            subprocess.check_output("qemu-img --version", shell=True)
        except subprocess.CalledProcessError as e:
            logging.exception(
                "Failed to determine qemu-img version. Make sure you have qemu-utils installed."
            )
            raise e

    def initialize_vm0_volume(self):
        try:
            subprocess.check_output(
                " ".join(
                    [
                        "qemu-img",
                        "create",
                        "-f",
                        "qcow2",
                        os.path.join(LIB_DIR, "volumes/vm-0.img"),
                        shlex.quote(disk_size),
                    ]
                ),
                shell=True,
            )
        except subprocess.CalledProcessError:
            logging.exception("Failed to create a new volume using qemu-img.")
            return

    def snapshot_vm0_volume(self):
        # We'll be using vm-0.img as backing storage
        pass

    def get_vm_disk_path(self, vm_id: int) -> str:
        return f"tap:qcow2:{LIB_DIR}/volumes/vm-{vm_id}.img,xvda,w"

    def rollback_vm_storage(self, vm_id: int):
        try:
            os.unlink(
                os.path.join(LIB_DIR, "volumes/vm-{vm_id}.img".format(vm_id=vm_id))
            )
        except FileNotFoundError:
            pass

        subprocess.run(
            [
                "qemu-img",
                "create",
                "-f",
                "qcow2",
                "-o",
                "backing_file=vm-0.img",
                os.path.join(LIB_DIR, "volumes/vm-{vm_id}.img".format(vm_id=vm_id)),
            ],
            check=True,
        )


def get_storage_backend(install_info: Dict[str, Any]) -> StorageBackendBase:
    backend_name = install_info["storage_backend"]

    backends = {
        "qcow2": Qcow2StorageBackend,
        "zfs": ZfsStorageBackend,
    }

    return backends[backend_name](install_info)

