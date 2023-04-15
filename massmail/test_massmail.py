import contextlib
import email as email_module
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

def parse_smtp(server):
    # we can not just issue a blank .read() because that would would block until
    # server.stderr is closed, which only happens after the server has exited
    # so we request 1MB (1024*1024 = 2^20 bytes = 1048576) to be sure
    smtp = server.stderr.read(1048576).decode()
    protocol = []
    emails = []
    for line in smtp.splitlines():
        if line.startswith('INFO:mail.log:'):
            # this is a line of protocol: SMTP server <-> SMTP client
            protocol.append(line)
        elif line.startswith('---------- MESSAGE FOLLOWS ----------'):
            # this lines starts a new email message
            email = []
        elif line.startswith('------------ END MESSAGE ------------'):
            # this line closes an email message
            # join all collected lines
            email = '\n'.join(email)
            # parse the whole thing as a string to get a Message object from
            # the email module
            emails.append(email_module.message_from_string(email,
                                            policy=email_module.policy.default))
        else:
            # collect this line, it belongs to the current email message
            email.append(line)
    protocol = '\n'.join(protocol)
    return protocol, emails

# just test that the cli is working and we get the right help text
def test_help(cli):
    result = cli.invoke(massmail, ['-h'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert 'Example:' in result.output


def test_regular_sending(cli, opts, server, good_parm, good_body):
    inp = ['--parameter', str(good_parm), '--body', str(good_body)]
    result = cli.invoke(massmail, opts + inp)
    assert result.exit_code == 0
    protocol, emails = parse_smtp(server)
    email = emails[0]

    # check that the envelope is correct
    assert 'sender: gorilla@jungle.com' in protocol
    assert 'recip: donkeys@jungle.com' in protocol

    # check that the headers are correct
    assert email['From'] == 'Blushing Gorilla <gorilla@jungle.com>'
    assert email['To'] == 'donkeys@jungle.com'
    assert email['Subject'] == 'Invitation to the jungle'
    assert 'Date' in email
    assert 'Message-ID' in email
    assert email.get_charsets() == ['utf-8']
    assert email.get_content_type() == 'text/plain'

    # check that we have insert the right values for our keys
    body = email.get_payload()
    assert 'Dear Alice Joyce' in body
    assert 'we kindly invite you to join us in the jungle' in body


def test_unicode_body_sending(cli, opts, server, good_parm, good_body):
    # add some unicode text to the body
    with good_body.open('at') as bodyf:
        bodyf.write('\nÜni©ödę¿\n')
    inp = ['--parameter', str(good_parm), '--body', str(good_body)]
    result = cli.invoke(massmail, opts + inp)
    assert result.exit_code == 0
    protocol, emails = parse_smtp(server)
    email = emails[0]
    body = email.get_payload()
    assert 'Üni©ödę¿' in body


def test_unicode_subject(cli, opts, server, good_parm, good_body):
    opts.extend(('--subject', 'Üni©ödę¿'))
    inp = ['--parameter', str(good_parm), '--body', str(good_body)]
    result = cli.invoke(massmail, opts + inp)
    assert result.exit_code == 0
    protocol, emails = parse_smtp(server)
    email = emails[0]
    assert email['Subject'] == 'Üni©ödę¿'

def test_unicode_from(cli, opts, server, good_parm, good_body):
    opts.extend(('--from', 'Üni©ödę¿ <broken@email.com>'))
    inp = ['--parameter', str(good_parm), '--body', str(good_body)]
    result = cli.invoke(massmail, opts + inp)
    assert result.exit_code == 0
    protocol, emails = parse_smtp(server)
    email = emails[0]
    assert email['From'] == 'Üni©ödę¿ <broken@email.com>'

def test_unicode_several_reciepients(cli, opts, server, good_parm, good_body):
    # add some unicode text to the body
    with good_parm.open('at') as parmf:
        parmf.write('\nJohn; Smith; j@monkeys.com\n')
    inp = ['--parameter', str(good_parm), '--body', str(good_body)]
    result = cli.invoke(massmail, opts + inp)
    assert result.exit_code == 0
    protocol, emails = parse_smtp(server)

    assert len(emails) == 2
    assert 'sender: gorilla@jungle.com' in protocol
    assert 'recip: donkeys@jungle.com' in protocol
    assert 'recip: j@monkeys.com' in protocol

    assert emails[0]['To'] == 'donkeys@jungle.com'
    assert emails[1]['To'] == 'j@monkeys.com'
    assert 'Dear Alice Joyce' in emails[0].get_payload()
    assert 'Dear John Smith' in emails[1].get_payload()

def test_unicode_parm(cli, opts, server, good_parm, good_body):
    # add some unicode text to the body
    with good_parm.open('at') as parmf:
        parmf.write('\nÜni©ödę¿; Smith; j@monkeys.com\n')
    inp = ['--parameter', str(good_parm), '--body', str(good_body)]
    result = cli.invoke(massmail, opts + inp)
    assert result.exit_code == 0
    protocol, emails = parse_smtp(server)
    assert 'Dear Üni©ödę¿ Smith' in emails[1].get_payload()
