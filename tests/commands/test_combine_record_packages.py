import json

from ocdskit.cli.__main__ import main
from tests import assert_command, run_command


def test_command(monkeypatch):
    assert_command(monkeypatch, main, ['combine-record-packages'],
                   ['record-package_minimal.json', 'record-package_maximal.json', 'record-package_extensions.json'],
                   ['combine-record-packages_minimal-maximal-extensions.json'])


def test_command_no_extensions(monkeypatch):
    assert_command(monkeypatch, main, ['combine-record-packages'],
                   ['record-package_minimal.json'],
                   ['combine-record-packages_minimal.json'])


def test_command_uri_published_date(monkeypatch):
    actual = run_command(monkeypatch, main, ['combine-record-packages', '--uri', 'http://example.com/x.json',
                                             '--published-date', '2010-01-01T00:00:00Z'],
                         ['record-package_minimal.json'])

    package = json.loads(actual)
    assert package['uri'] == 'http://example.com/x.json'
    assert package['publishedDate'] == '2010-01-01T00:00:00Z'


def test_command_publisher(monkeypatch):
    actual = run_command(monkeypatch, main, ['combine-record-packages', '--publisher-name', 'Acme Inc.'],
                         ['record-package_minimal.json'])

    package = json.loads(actual)
    assert package['publisher']['name'] == 'Acme Inc.'
