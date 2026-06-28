import subprocess

CMD_EXE = "/mnt/c/Windows/System32/cmd.exe"
POWERSHELL_EXE = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"

VK_CODES: dict[str, int] = {
    "play_pause": 0xB3,
    "next": 0xB0,
    "prev": 0xB1,
    "vol_up": 0xAF,
    "vol_down": 0xAE,
    "vol_mute": 0xAD,
}

_PS_ADDTYPE = (
    "Add-Type -MemberDefinition '"
    '[DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);'
    "' -Name 'User32' -Namespace 'Win32' -ErrorAction SilentlyContinue;"
)


def send_key(vk_code: int, times: int = 1) -> None:
    press = (
        f"[Win32.User32]::keybd_event({hex(vk_code)}, 0, 0, [UIntPtr]::Zero);"
        f"[Win32.User32]::keybd_event({hex(vk_code)}, 0, 2, [UIntPtr]::Zero);"
    )
    script = _PS_ADDTYPE + press * times
    subprocess.run([POWERSHELL_EXE, "-Command", script], check=True)