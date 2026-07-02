import subprocess

VK_CODES: dict[str, int] = {
    "play_pause": 0xB3,
    "next": 0xB0,
    "prev": 0xB1,
    "vol_up": 0xAF,
    "vol_down": 0xAE,
    "vol_mute": 0xAD,
}

_PS_KEY_SCRIPT = (
    "Add-Type -MemberDefinition '"
    '[DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);'
    "' -Name 'User32' -Namespace 'Win32' -ErrorAction SilentlyContinue;"
    "[Win32.User32]::keybd_event({vk}, 0, 0, 0);"
    "[Win32.User32]::keybd_event({vk}, 0, 2, 0)"
)


def send_key(vk_code: int) -> None:
    script = _PS_KEY_SCRIPT.format(vk=hex(vk_code))
    subprocess.run(["powershell.exe", "-Command", script], check=True)

 