import sys
import os.path
from io import BytesIO, StringIO, TextIOWrapper
from unittest.mock import patch

import pytest


def path(filename):
    return os.path.join('tests', 'fixtures', filename)


def read(filename, mode='rt', encoding=None, **kwargs):
    with open(path(filename), mode, encoding=encoding, **kwargs) as f:
        return f.read()


def run_stdout(monkeypatch, main, args):
    with patch('sys.stdout', new_callable=StringIO) as stdout:
        monkeypatch.setattr(sys, 'argv', ['ocdskit'] + args)
        main()

    return stdout.getvalue()


# Similar to `stdout`, but with `pytest.raises` block.
def run_stdout_error(monkeypatch, main, args, error=SystemExit):
    with pytest.raises(error) as excinfo:
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            monkeypatch.setattr(sys, 'argv', ['ocdskit'] + args)
            main()

    assert stdout.getvalue() == ''

    return excinfo


def assert_stdout(monkeypatch, main, args, expected):
    actual = run_stdout(monkeypatch, main, args)

    if os.path.isfile(path(expected)):
        expected = read(expected, newline='')

    assert actual == expected


def run_command(monkeypatch, main, args, stdin):
    if not isinstance(stdin, bytes):
        stdin = b''.join(read(filename, 'rb') for filename in stdin)

    with patch('sys.stdin', TextIOWrapper(BytesIO(stdin))), patch('sys.stdout', new_callable=StringIO) as stdout:
        monkeypatch.setattr(sys, 'argv', ['ocdskit'] + args)
        main()

    return stdout.getvalue()


# Similar to `run_command`, but with `pytest.raises` block.
def run_command_error(monkeypatch, main, args, stdin, error=SystemExit):
    if not isinstance(stdin, bytes):
        stdin = b''.join(read(filename, 'rb') for filename in stdin)

    with pytest.raises(error) as excinfo:
        with patch('sys.stdin', TextIOWrapper(BytesIO(stdin))), patch('sys.stdout', new_callable=StringIO) as stdout:
            monkeypatch.setattr(sys, 'argv', ['ocdskit'] + args)
            main()

    assert stdout.getvalue() == ''

    return excinfo


def assert_command(monkeypatch, main, args, stdin, expected):
    actual = run_command(monkeypatch, main, args, stdin)

    if not isinstance(expected, str):
        expected = ''.join(read(filename) for filename in expected)

    assert actual == expected
