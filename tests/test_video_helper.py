import json
from unittest.mock import patch, MagicMock

from helpers.video_helper import get_video_dimensions


def test_returns_dimensions_on_success():
    fake_output = json.dumps({"streams": [{"width": 1920, "height": 1080}]})
    with patch("helpers.video_helper.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=fake_output)
        dims = get_video_dimensions(b"\x00" * 10)
    assert dims == (1920, 1080)


def test_returns_none_on_failure():
    with patch("helpers.video_helper.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        dims = get_video_dimensions(b"\x00" * 10)
    assert dims is None


def test_returns_none_on_exception():
    with patch("helpers.video_helper.subprocess.run", side_effect=Exception("fail")):
        dims = get_video_dimensions(b"\x00" * 10)
    assert dims is None


def test_returns_none_when_no_streams():
    fake_output = json.dumps({"streams": []})
    with patch("helpers.video_helper.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=fake_output)
        dims = get_video_dimensions(b"\x00" * 10)
    assert dims is None
