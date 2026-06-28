from unittest.mock import patch
import subprocess
from handlers.base import send_key, VK_CODES


def test_send_key_calls_powershell():
    with patch("handlers.base.subprocess.run") as mock_run:
        send_key(VK_CODES["play_pause"])
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "powershell.exe" in cmd
        assert "0xb3" in " ".join(str(a) for a in cmd)


def test_send_key_raises_on_failure():
    with patch("handlers.base.subprocess.run", side_effect=subprocess.CalledProcessError(1, "ps")):
        try:
            send_key(VK_CODES["play_pause"])
            assert False, "debería haber lanzado excepción"
        except subprocess.CalledProcessError:
            pass