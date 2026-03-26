import argparse

from mara_host.cli.commands.build.upload import DEFAULT_DIRECT_UPLOAD_BAUD, cmd_upload


def _args(**overrides):
    base = {
        "env": "esp32_usb",
        "verbose": False,
        "port": "/dev/ttyUSB0",
        "features": None,
        "preset": None,
        "no_features": None,
        "dry_run": False,
        "generate": False,
        "upload_baud": None,
        "direct": False,
        "auto_retry_direct": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_cmd_upload_passes_direct_options(monkeypatch):
    calls = []

    def fake_upload(env, verbose, features, port=None, upload_baud=None, direct=False):
        calls.append(
            {
                "env": env,
                "verbose": verbose,
                "features": features,
                "port": port,
                "upload_baud": upload_baud,
                "direct": direct,
            }
        )
        return 0

    monkeypatch.setattr("mara_host.cli.commands.build.upload.do_upload", fake_upload)

    rc = cmd_upload(_args(upload_baud=57600, direct=True))

    assert rc == 0
    assert calls == [
        {
            "env": "esp32_usb",
            "verbose": False,
            "features": None,
            "port": "/dev/ttyUSB0",
            "upload_baud": 57600,
            "direct": True,
        }
    ]


def test_cmd_upload_auto_retries_direct_on_failure(monkeypatch):
    calls = []

    def fake_upload(env, verbose, features, port=None, upload_baud=None, direct=False):
        calls.append(
            {
                "env": env,
                "verbose": verbose,
                "features": features,
                "port": port,
                "upload_baud": upload_baud,
                "direct": direct,
            }
        )
        return 7 if len(calls) == 1 else 0

    monkeypatch.setattr("mara_host.cli.commands.build.upload.do_upload", fake_upload)

    rc = cmd_upload(_args(auto_retry_direct=True))

    assert rc == 0
    assert calls == [
        {
            "env": "esp32_usb",
            "verbose": False,
            "features": None,
            "port": "/dev/ttyUSB0",
            "upload_baud": None,
            "direct": False,
        },
        {
            "env": "esp32_usb",
            "verbose": False,
            "features": None,
            "port": "/dev/ttyUSB0",
            "upload_baud": DEFAULT_DIRECT_UPLOAD_BAUD,
            "direct": True,
        },
    ]


def test_cmd_upload_does_not_retry_direct_without_port(monkeypatch):
    calls = []

    def fake_upload(env, verbose, features, port=None, upload_baud=None, direct=False):
        calls.append((port, upload_baud, direct))
        return 9

    monkeypatch.setattr("mara_host.cli.commands.build.upload.do_upload", fake_upload)

    rc = cmd_upload(_args(port=None, auto_retry_direct=True))

    assert rc == 9
    assert calls == [(None, None, False)]
