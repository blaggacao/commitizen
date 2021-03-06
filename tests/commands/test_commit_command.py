import os

import pytest

from commitizen import cmd, commands
from commitizen.cz.exceptions import CzException


@pytest.fixture
def staging_is_clean(mocker):
    is_staging_clean_mock = mocker.patch("commitizen.git.is_staging_clean")
    is_staging_clean_mock.return_value = False


@pytest.mark.usefixtures("staging_is_clean")
def test_commit(config, mocker):
    prompt_mock = mocker.patch("questionary.prompt")
    prompt_mock.return_value = {
        "prefix": "feat",
        "subject": "user created",
        "scope": "",
        "is_breaking_change": False,
        "body": "",
        "footer": "",
    }

    commit_mock = mocker.patch("commitizen.git.commit")
    commit_mock.return_value = cmd.Command("success", "", "", "")
    success_mock = mocker.patch("commitizen.out.success")

    commands.Commit(config, {})()
    success_mock.assert_called_once()


@pytest.mark.usefixtures("staging_is_clean")
def test_commit_retry_fails_no_backup(config, mocker):
    commit_mock = mocker.patch("commitizen.git.commit")
    commit_mock.return_value = cmd.Command("success", "", "", "")

    with pytest.raises(SystemExit):
        commands.Commit(config, {"retry": True})()


@pytest.mark.usefixtures("staging_is_clean")
def test_commit_retry_works(config, mocker):
    prompt_mock = mocker.patch("questionary.prompt")
    prompt_mock.return_value = {
        "prefix": "feat",
        "subject": "user created",
        "scope": "",
        "is_breaking_change": False,
        "body": "closes #21",
        "footer": "",
    }

    commit_mock = mocker.patch("commitizen.git.commit")
    commit_mock.return_value = cmd.Command("", "error", "", "")
    error_mock = mocker.patch("commitizen.out.error")

    with pytest.raises(SystemExit):
        commit_cmd = commands.Commit(config, {})
        temp_file = commit_cmd.temp_file
        commit_cmd()

    prompt_mock.assert_called_once()
    error_mock.assert_called_once()
    assert os.path.isfile(temp_file)

    # Previous commit failed, so retry should pick up the backup commit
    # commit_mock = mocker.patch("commitizen.git.commit")
    commit_mock.return_value = cmd.Command("success", "", "", "")
    success_mock = mocker.patch("commitizen.out.success")

    commands.Commit(config, {"retry": True})()

    commit_mock.assert_called_with("feat: user created\n\ncloses #21")
    prompt_mock.assert_called_once()
    success_mock.assert_called_once()
    assert not os.path.isfile(temp_file)


@pytest.mark.usefixtures("staging_is_clean")
def test_commit_command_with_dry_run_option(config, mocker):
    prompt_mock = mocker = mocker.patch("questionary.prompt")
    prompt_mock.return_value = {
        "prefix": "feat",
        "subject": "user created",
        "scope": "",
        "is_breaking_change": False,
        "body": "closes #57",
        "footer": "",
    }

    with pytest.raises(SystemExit):
        commit_cmd = commands.Commit(config, {"dry_run": True})
        commit_cmd()


def test_commit_when_nothing_to_commit(config, mocker):
    is_staging_clean_mock = mocker.patch("commitizen.git.is_staging_clean")
    is_staging_clean_mock.return_value = True

    with pytest.raises(SystemExit) as err:
        commit_cmd = commands.Commit(config, {})
        commit_cmd()

    assert err.value.code == commands.commit.NOTHING_TO_COMMIT


@pytest.mark.usefixtures("staging_is_clean")
def test_commit_when_customized_expected_raised(config, mocker, capsys):
    _err = ValueError()
    _err.__context__ = CzException("This is the root custom err")
    prompt_mock = mocker.patch("questionary.prompt")
    prompt_mock.side_effect = _err

    with pytest.raises(SystemExit) as err:
        commit_cmd = commands.Commit(config, {})
        commit_cmd()

    assert err.value.code == commands.commit.CUSTOM_ERROR

    # Assert only the content in the formatted text
    captured = capsys.readouterr()
    assert "This is the root custom err" in captured.err
