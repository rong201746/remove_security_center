# Windows Security Center Removal Tool

A Python script that attempts to disable and remove Windows Security Center
(Windows Defender, SecurityHealthService, WSCSVC) components in order to
reclaim disk space.

## WARNING

This tool is destructive and dangerous.

- It removes the primary antivirus and security services of Windows.
- It modifies protected registry keys and deletes system service registrations.
- It can break Windows Update, cause boot failures, and void your warranty.
- Modern Windows uses Tamper Protection and Secure Boot, which may silently
  restore or block these changes.
- Do NOT run this on any machine you care about or that stores important data.

The author provides no warranty and accepts no liability for data loss,
system damage, or security breaches resulting from use of this script.

## Requirements

- Windows 10 or Windows 11
- Python 3.8 or newer
- Administrator privileges (the script will request UAC elevation)

## Usage

1. Open a terminal.
2. Run:
```bash
python remove_security_center.py
```

3. Approve the UAC prompt.
4. Reboot when finished.

## What It Does

1. Stops and disables Defender and Security Center services via `sc config`.
2. Writes policy registry values under
`HKLM\SOFTWARE\Policies\Microsoft\Windows Defender`.
3. Deletes cached definition, quarantine, and health data folders.
4. Deletes the service registrations with `sc delete`.

## What It Cannot Do

- Bypass Tamper Protection (you must disable it manually in the Windows
Security UI before running).
- Remove Defender on Windows builds where it is integrated into the kernel
and protected by Secure Boot.
- Guarantee that the components stay removed after a Windows Update.

## Reverting

If you need to restore protection:
```bash
sc config WinDefend start= auto
sc config wscsvc start= auto
sc config SecurityHealthService start= auto
sc start WinDefend
```

2. Delete the policy registry keys created by this script under
`HKLM\SOFTWARE\Policies\Microsoft\Windows Defender`.
3. Run `sfc /scannow` and `DISM /Online /Cleanup-Image /RestoreHealth`.
4. Reboot.

## License

GNU GENERAL PUBLIC LICENSE v3.0

1. Re-enable services:
