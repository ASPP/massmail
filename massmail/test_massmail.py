import contextlib
import email
import io
import sys
import os
import time
import subprocess
import base64

from massmail.massmail import main as massmail
import click.testing
import pytest

# run the script from the command line through the click-internal testing interface
@pytest.fixture
def cli():
    return click.testing.CliRunner()

# return the list of monimal required options to run massmail without errors
@pytest.fixture
def opts():
    return ['--from', 'Blushing Gorilla <gorilla@jungle.com>',
            '--subject', 'Invitation to the jungle',
            '--server', 'localhost:8025',
            '--force',
            '--no-tls']


# return a locally running SMTP server. This fixture kills the server after the
# test run is finished, i.e. not after every test!
# The resulting server runs at localhost:8025
@pytest.fixture(scope="module")
def server():
    server = subprocess.Popen([sys.executable,
                               '-m', 'aiosmtpd',
                               '-n',
                               '-d',
                               '-l',  'localhost:8025',
                               '-c', 'aiosmtpd.handlers.Debugging', 'stderr'],
                              stdin=None,
                              text=False,
                              stderr=subprocess.PIPE,
                              stdout=None,
                              bufsize=0,
                              env={'AIOSMTPD_CONTROLLER_TIMEOUT':'0'})
    # give the smtp server 100 milliseconds to startup
    time.sleep(0.1)
    yield server
    server.terminate()

# return a "good" parameter file
@pytest.fixture
def good_parm(tmp_path):
    header = '$NAME$;$SURNAME$;$EMAIL$'
    row1 = 'Alice;Joyce;donkeys@jungle.com'
    f = tmp_path / 'parms.csv'
    f.write_text(header+'\n'+row1)
    yield f
    f.unlink()

# return a "good" body file
@pytest.fixture
def good_body(tmp_path):
    body = """Dear $NAME$ $SURNAME$,

    we kindly invite you to join us in the jungle

    Cheers,
    Gorilla
    """
    f = tmp_path / 'body.txt'
    f.write_text(body)
    yield f
    f.unlink()

# just test that the cli is working and we get the right help text
def test_help(cli):
    result = cli.invoke(massmail, ['-h'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert 'Example:' in result.output


def test_regular_sending(cli, opts, server, good_parm, good_body):
    inp = ['--parameter', str(good_parm), '--body', str(good_body)]
    result = cli.invoke(massmail, opts + inp)
    # we can not just issue a blank .read() because that would would block until
    # server.stderr is closed, which only happens after the server has exited
    smtp = server.stderr.read(100000).decode('ascii')
    assert result.exit_code == 0
    assert 'Dear Alice Joyce' in smtp

