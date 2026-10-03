"""
remove_security_center.py

Attempts to disable/remove Windows Security Center (Windows Defender,
SecurityHealthService, WSCSVC, etc.) components.

Requires Administrator privileges. The script will attempt to re-launch
itself with a UAC elevation prompt if not already elevated.

DISCLAIMER:
    This script modifies critical system services and registry keys.
    Doing so can:
      - Leave your computer completely unprotected.
      - Break Windows Update, Defender, and third-party AV integration.
      - Cause boot failures or Blue Screens.
    Use only on disposable/test machines. No warranty is provided.
"""

import ctypes
import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# Services and registry paths related to Windows Security Center / Defender.
# Adjust with caution. Some names differ between Windows versions.
# ---------------------------------------------------------------------------
SERVICES_TO_DISABLE = [
    "WinDefend",          # Microsoft Defender Antivirus Service
    "WdNisSvc",           # Microsoft Defender Network Inspection Service
    "SecurityHealthService",  # Windows Security Service (tray/UI)
    "wscsvc",             # Security Center
    "Sense",              # Microsoft Defender ATP / EDR
    "MsSense",            # Microsoft Defender for Endpoint
    "WdBoot",             # Defender Boot driver (disabling may be refused)
    "WdFilter",           # Defender Minifilter driver
    "WdNisDrv",           # Defender Network Inspection driver
]

# Registry keys that control Defender / Security Center behavior.
# Setting DisableAntiSpyware etc. is blocked by Tamper Protection on
# modern Windows builds; the script reports failures instead of crashing.
REGISTRY_KEYS = [
    (r"SOFTWARE\Policies\Microsoft\Windows Defender", "DisableAntiSpyware", 1),
    (r"SOFTWARE\Policies\Microsoft\Windows Defender", "DisableAntiVirus", 1),
    (r"SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection",
     "DisableRealtimeMonitoring", 1),
    (r"SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection",
     "DisableBehaviorMonitoring", 1),
    (r"SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection",
     "DisableOnAccessProtection", 1),
    (r"SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection",
     "DisableScanOnRealtimeEnable", 1),
    (r"SOFTWARE\Policies\Microsoft\Windows\Windows Defender", "DisableAntiSpyware", 1),
]

# Folders that store Defender definitions/quarantine. Removing these frees
# disk space but Windows will recreate them on next update if Defender runs.
FOLDERS_TO_REMOVE = [
    r"C:\ProgramData\Microsoft\Windows Defender",
    r"C:\ProgramData\Microsoft\Windows Defender Advanced Threat Protection",
    r"C:\ProgramData\Microsoft\Windows Security Health",
]


def is_admin() -> bool:
    """Return True if the current process has Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate_and_rerun() -> None:
    """
    Re-launch this script with UAC elevation using ShellExecuteW 'runas'.
    Exits the current process afterwards.
    """
    script = os.path.abspath(__file__)
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    # ShellExecuteW returns a value > 32 on success.
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}" {params}', None, 1
    )
    if result <= 32:
        print("[!] UAC elevation was denied or failed. Exiting.")
    sys.exit(0)


def run(cmd: list[str]) -> tuple[int, str]:
    """Run a command silently and return (returncode, combined_output)."""
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return proc.returncode, proc.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return -1, str(exc)


def disable_service(name: str) -> None:
    """Stop a service and set its startup type to Disabled."""
    print(f"[*] Service: {name}")
    rc, out = run(["sc", "stop", name])
    print(f"    stop  -> rc={rc} {out}")
    rc, out = run(["sc", "config", name, "start=", "disabled"])
    print(f"    config-> rc={rc} {out}")


def delete_service(name: str) -> None:
    """Delete a service registration entirely (more destructive)."""
    print(f"[*] Deleting service: {name}")
    rc, out = run(["sc", "delete", name])
    print(f"    delete-> rc={rc} {out}")


def set_registry_values() -> None:
    """Write policy registry values to disable Defender features."""
    import winreg  # imported lazily so the module loads on non-Windows for lint

    for path, value_name, value in REGISTRY_KEYS:
        try:
            key = winreg.CreateKeyEx(
                winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, value)
            winreg.CloseKey(key)
            print(f"[+] Registry set: HKLM\\{path}\\{value_name} = {value}")
        except PermissionError:
            print(f"[!] Access denied (Tamper Protection?): HKLM\\{path}\\{value_name}")
        except Exception as exc:  # noqa: BLE001
            print(f"[!] Failed HKLM\\{path}\\{value_name}: {exc}")


def remove_folder(path: str) -> None:
    """
    Best-effort recursive deletion of a folder. Files locked by the OS are
    skipped; failures are reported instead of raising.
    """
    import shutil

    if not os.path.isdir(path):
        print(f"[=] Not present, skipping: {path}")
        return
    try:
        shutil.rmtree(path, ignore_errors=True)
        if os.path.isdir(path):
            print(f"[!] Partially removed (some files locked): {path}")
        else:
            print(f"[+] Removed: {path}")
    except Exception as exc:  # noqa: BLE001
        print(f"[!] Could not remove {path}: {exc}")


def main() -> None:
    if os.name != "nt":
        print("[!] This script only runs on Windows.")
        sys.exit(1)

    if not is_admin():
        print("[*] Administrator rights required. Requesting UAC elevation...")
        elevate_and_rerun()

    print("=" * 70)
    print(" Windows Security Center Removal")
    print(" This WILL reduce system protection and is NOT recommended.")
    print("=" * 70)

    print("\n[Phase 1] Disabling services")
    for svc in SERVICES_TO_DISABLE:
        disable_service(svc)

    print("\n[Phase 2] Writing policy registry values")
    set_registry_values()

    print("\n[Phase 3] Removing data folders (frees disk space)")
    for folder in FOLDERS_TO_REMOVE:
        remove_folder(folder)

    print("\n[Phase 4] Deleting service registrations (aggressive)")
    for svc in SERVICES_TO_DISABLE:
        delete_service(svc)

    print("\n[!] Done. A reboot is recommended.")
    print("[!] Note: Tamper Protection, Secure Boot, and Windows Update may")
    print("    restore these components automatically. To truly remove them")
    print("    you must also disable Tamper Protection in the Windows")
    print("    Security UI and use offline registry editing or a modified")
    print("    installation image.")


if __name__ == "__main__":
    main()
