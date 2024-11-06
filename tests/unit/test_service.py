"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import multiprocessing
from time import sleep

import httpx
from box import Box

from softpack_core import __version__
from softpack_core.app import app
from softpack_core.config.models import EmailConfig
from softpack_core.service import ServiceAPI, send_email


def test_service_run() -> None:
    run = multiprocessing.Process(target=ServiceAPI.run)
    run.start()
    while True:
        try:
            response = httpx.get(app.url())
            break
        except httpx.RequestError:
            if not run.is_alive():
                raise Exception("Service failed to start.")
            sleep(5)
    run.terminate()
    status = Box(response.json())
    assert status.softpack.core.version == __version__


def test_send_email(mocker):
    mock_SMTP = mocker.MagicMock(name="smtplib.SMTP")
    mocker.patch("smtplib.SMTP", new=mock_SMTP)

    emailConfig = EmailConfig(
        fromAddr="test@domain.com",
        toAddr="test2@domain.com",
        smtp="host.mail.com",
    )

    send_email(emailConfig, "MESSAGE1", "SUBJECT1", "USERNAME")

    assert mock_SMTP.call_args[0] == ("host.mail.com",)
    assert mock_SMTP.call_args[1] == {"local_hostname": None}

    assert mock_SMTP.return_value.sendmail.call_count == 1
    assert (
        mock_SMTP.return_value.sendmail.call_args[0][0] == emailConfig.fromAddr
    )
    assert mock_SMTP.return_value.sendmail.call_args[0][1] == [
        emailConfig.toAddr
    ]
    assert "MESSAGE1" in mock_SMTP.return_value.sendmail.call_args[0][2]
    assert "SUBJECT1" in mock_SMTP.return_value.sendmail.call_args[0][2]

    emailConfig = EmailConfig(
        fromAddr="{}@domain.com",
        toAddr="{}@other-domain.com",
        smtp="host.mail.com",
        localHostname="something",
    )

    send_email(emailConfig, "MESSAGE2", "SUBJECT2", "USERNAME2")

    assert mock_SMTP.return_value.sendmail.call_count == 2
    assert mock_SMTP.call_args[1] == {"local_hostname": "something"}
    assert (
        mock_SMTP.return_value.sendmail.call_args[0][0]
        == "USERNAME2@domain.com"
    )
    assert mock_SMTP.return_value.sendmail.call_args[0][1] == [
        "USERNAME2@other-domain.com"
    ]

    assert "MESSAGE2" in mock_SMTP.return_value.sendmail.call_args[0][2]
    assert "SUBJECT2" in mock_SMTP.return_value.sendmail.call_args[0][2]

    emailConfig = EmailConfig()

    send_email(emailConfig, "MESSAGE3", "SUBJECT3", "USERNAME3")
    assert mock_SMTP.return_value.sendmail.call_count == 2
