import email as email_module
import subprocess
import sys
import time

from massmail.massmail import main as massmail
import click.testing
import pytest




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
def parm(tmp_path):
    header = '$NAME$;$SURNAME$;$EMAIL$'
    row1 = 'Alice;Joyce;donkeys@jungle.com'
    f = tmp_path / 'parms.csv'
    f.write_text(header+'\n'+row1)
    yield f
    f.unlink()

# return a "good" body file
@pytest.fixture
def body(tmp_path):
    text = """Dear $NAME$ $SURNAME$,

    we kindly invite you to join us in the jungle

    Cheers,
    Gorilla
    """
    f = tmp_path / 'body.txt'
    f.write_text(text)
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

def cli(server, parm, body, opts=[]):
    options  = ['--from', 'Blushing Gorilla <gorilla@jungle.com>',
            '--subject', 'Invitation to the jungle',
            '--server', 'localhost:8025',
            '--force',
            '--no-tls'] + opts + ['--parameter', str(parm), '--body', str(body)]
    script = click.testing.CliRunner()
    result = script.invoke(massmail, options)
    assert result.exit_code == 0
    protocol, emails = parse_smtp(server)
    return protocol, emails

# just test that the cli is working and we get the right help text
def test_help():
    result = click.testing.CliRunner().invoke(massmail, ['-h'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
    assert 'Example:' in result.output

def test_regular_sending(server, parm, body):
    protocol, emails = cli(server, parm, body)
    email = emails[0]

    # check that the envelope is correct
    assert 'sender: gorilla@jungle.com' in protocol
    assert 'recip: donkeys@jungle.com' in protocol

    # email is ASCII, so the transfer encoding should be 7bit
    assert email['Content-Transfer-Encoding'] == '7bit'

    # check that the headers are correct
    assert email['From'] == 'Blushing Gorilla <gorilla@jungle.com>'
    assert email['To'] == 'donkeys@jungle.com'
    assert email['Subject'] == 'Invitation to the jungle'
    assert 'Date' in email
    assert 'Message-ID' in email
    assert email.get_charsets() == ['utf-8']
    assert email.get_content_type() == 'text/plain'

    # check that we have insert the right values for our keys
    text = email.get_payload()
    assert 'Dear Alice Joyce' in text
    assert 'we kindly invite you to join us in the jungle' in text


def test_unicode_body_sending(server, parm, body):
    # add some unicode text to the body
    with body.open('at') as bodyf:
        bodyf.write('\nÜni©ödę¿\n')
    protocol, emails = cli(server, parm, body)
    email = emails[0]
    # unicode characters force the transfer encoding to  8bit
    assert email['Content-Transfer-Encoding'] == '8bit'
    text = email.get_payload()
    assert 'Üni©ödę¿' in text

def test_wild_unicode_body_sending(server, parm, body):
    # add some unicode text to the body
    with body.open('at') as bodyf:
        bodyf.write('\nœ´®†¥¨ˆøπ¬˚∆˙©ƒ∂ßåΩ≈ç√∫˜µ≤ユーザーコードa😀\n')
    protocol, emails = cli(server, parm, body)
    email = emails[0]
    # because we use unicode characters that don't fit in one byte,
    # the email will be encoded in base64 for tranfer
    assert email['Content-Transfer-Encoding'] == 'base64'
    # because the text contains, we trust the internal email_module machinery
    # to perform the proper decoding
    text = email.get_content()
    assert 'œ´®†¥¨ˆøπ¬˚∆˙©ƒ∂ßåΩ≈ç√∫˜µ≤ユーザーコードa😀' in text

def test_unicode_subject(server, parm, body):
    opts = ['--subject', 'Üni©ödę¿']
    protocol, emails = cli(server, parm, body, opts=opts)
    email = emails[0]
    assert email['Subject'] == 'Üni©ödę¿'

def test_unicode_from(server, parm, body):
    opts = ['--from', 'Üni©ödę¿ <broken@email.com>']
    protocol, emails = cli(server, parm, body, opts=opts)
    email = emails[0]
    assert email['From'] == 'Üni©ödę¿ <broken@email.com>'

def test_unicode_several_reciepients(server, parm, body):
    # add some unicode text to the body
    with parm.open('at') as parmf:
        parmf.write('\nJohn; Smith; j@monkeys.com\n')
    protocol, emails = cli(server, parm, body)

    assert len(emails) == 2
    assert 'sender: gorilla@jungle.com' in protocol
    assert 'recip: donkeys@jungle.com' in protocol
    assert 'recip: j@monkeys.com' in protocol

    assert emails[0]['To'] == 'donkeys@jungle.com'
    assert emails[1]['To'] == 'j@monkeys.com'
    assert 'Dear Alice Joyce' in emails[0].get_payload()
    assert 'Dear John Smith' in emails[1].get_payload()

def test_unicode_parm(server, parm, body):
    # add some unicode text to the body
    with parm.open('at') as parmf:
        parmf.write('\nÜni©ödę¿; Smith; j@monkeys.com\n')
    protocol, emails = cli(server, parm, body)
    assert 'Dear Üni©ödę¿ Smith' in emails[1].get_payload()
