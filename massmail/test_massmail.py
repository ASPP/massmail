import email as email_module
import subprocess
import sys
import time

from massmail.massmail import main as massmail
import click.testing
import pytest

# 4096 bit, valid until year 2123
# generated with:
# openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 36500 -nodes -subj '/CN=localhost'
TLS_KEY="""-----BEGIN PRIVATE KEY-----
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
sBuZkVRS+PJe57phZv06aFFrv2VcXXg=
-----END PRIVATE KEY-----
"""

TLS_CERT="""-----BEGIN CERTIFICATE-----
MIIFCzCCAvOgAwIBAgIULLLAwLBYIJVgJ/39zhjZq+YnzkcwDQYJKoZIhvcNAQEL
BQAwFDESMBAGA1UEAwwJbG9jYWxob3N0MCAXDTIzMDQxNjEyMjIyMFoYDzIxMjMw
MzIzMTIyMjIwWjAUMRIwEAYDVQQDDAlsb2NhbGhvc3QwggIiMA0GCSqGSIb3DQEB
AQUAA4ICDwAwggIKAoICAQDL+HYMRZ21L8EhaR0wBgiK9ww/51iNYSKVffXphnt7
7B1o5A80m98B3v9epY48jE+Cbytl9PxlWHcnjlGWqO/xSFiETmJokRcBr1s8Ij0t
ZYc2PuPwpLm+wN3rn1JX4wuskSXaxnDtUgZgt7GYIsVxpg5qIdvMiV/68sho0pG9
Y4LSw+mwy2rIXOwpCWuV0PKOq64++oK2P1N7x+B0iyWHvQd+SLKK7yLQr2Sh5iPq
14KJkBe2mWjoujtGxo8Cp4aYE1nVAF1VV0BxPsp8xsKo6DEcljIw3MfI4gdYUYax
QPWmWb9141iMCoeCkAqrnSSUFdRf6QUhfesumNGyIx/d7iE5LsTT9i0kMdemM5R3
b9IEwD6EXlJDOVKTZnw2tKqbBnzeIpeRF/qZHevOnhLc6AewJacEURFG2TNgkxCJ
3SwFdzgIWbYz64J85Q8Bu3e0s4WUjl2XRgsaIDAYn6tYWndMbGiHfjx60R153lIx
HWAu+bAsV15WDI+s1wJT7RjG0Xs37WEcGhK44eFdMtb9cKmWGFIFEhWx/6iFwRk/
uPptE+QgMiuEkydUidw/6hQ0vJKnwFRCOcFari4SrUgpgMjKsxNyAosGvi+cE7U7
XmtbOOpKGeL1y05JFnUucaQfuCLzaiiI1V/RHlaeU0ZNk3EQl09coNCzJtjxhHDv
cwIDAQABo1MwUTAdBgNVHQ4EFgQU3PuRab4JVPITf+ICU5HVOMpW0gIwHwYDVR0j
BBgwFoAU3PuRab4JVPITf+ICU5HVOMpW0gIwDwYDVR0TAQH/BAUwAwEB/zANBgkq
hkiG9w0BAQsFAAOCAgEAOkEwnaMyxc7NdJedwk5sl6yoP/yY/rKDKA1yCEwgolkF
k73F5VcaOcVhwoA/a2h8AwYOQTGv2YNZnRxLskooyKkLrbHoZn34/YO1kgaXAm/p
mtiVsdaoFxUrcE7GXkJDTz4cC8wHc8BFrK6xESk8FYl07DCjIK9kFBzTGLV234kR
OLpvFAoFbvVWlWDT3VLIGjP6EIp7JFE/neTpB8PguZ7dcNdgtoiWz19Pv3JYoWWj
DTSZXJgu6OUjVxWC0T1VBz/uv5n9GNEjLa23hdzhztigmcrOKgrX43cTzNhnu62R
6Tx1HUtkswvxNzhaEKt3TP6Jde7mP5J6DKi1HpfKuGDizFJzoEkmWQNfeCzWniw8
W01qwU2xZ9AETQB2uAWoHF0vKRX8ZuzOBhK1vW9HVtSZFHJZ3OaS5/5TNvts8fvs
eK5DIjBOr2RQqw+V9JYoBPr3t8EUE1cBSI6THlkWMDvXm5wal0tZOF7HGjCxXnHY
Z7tS2M2dLHwsnOultNrtZn+zjSmmce2/YQzNqZcax5G9kTuU88OguqcDdB3pcWzY
U1iY1r9bTWpfIASnDpYz3RbE9jp5+ZgNjhA6l5lXk9/CHBQWyxL9d2Khp+3IV0t9
TfvhHNbB/2KiW9Si3G4bfcyPrH60O9yCfmbLDUjRgH2UjbOIefWKcKyAz/ZA5Y0=
-----END CERTIFICATE-----
"""

# return a locally running SMTP server. This fixture kills the server after the
# test run is finished, i.e. not after every test!
# The resulting server runs at localhost:8025
@pytest.fixture(scope="module")
def server(tmp_path_factory):
    tlsdir = tmp_path_factory.mktemp('tlsdir')
    key = tlsdir / 'key'
    key.write_text(TLS_KEY)
    cert = tlsdir / 'cert'
    cert.write_text(TLS_CERT)
    server = subprocess.Popen([sys.executable,
                               '-m', 'aiosmtpd',
                               '--nosetuid',
                               '--debug',
                               '--tlscert', str(cert),
                               '--tlskey', str(key),
                               '--listen',  'localhost:8025',
                               '--class', 'aiosmtpd.handlers.Debugging', 'stderr'],
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
    smtp = server.stderr.read(1048576)
    protocol = []
    emails = []
    for line in smtp.splitlines():
        if line.startswith(b'INFO:mail.log:'):
            # this is a line of protocol: SMTP server <-> SMTP client
            protocol.append(line)
        elif line.startswith(b'---------- MESSAGE FOLLOWS ----------'):
            # this lines starts a new email message
            email = []
        elif line.startswith(b'------------ END MESSAGE ------------'):
            # this line closes an email message
            # join all collected lines
            email = b'\n'.join(email) # we are dealing with bytes here
            # parse the whole thing to get a EmailMessage object from the email module
            emails.append(email_module.message_from_bytes(email,
                                            policy=email_module.policy.default))
        else:
            # collect this line, it belongs to the current email message
            email.append(line)
    protocol = b'\n'.join(protocol)
    # protocol chat should always be ascii, if we get a UnicodeDecodeError here
    # we'll have to examine the server output to understand what's up
    protocol = protocol.decode('ascii')
    return protocol, emails

# wrapper for running the massmail script and parse the SMTP server output
def cli(server, parm, body, opts={}, opts_list=[], errs=False):
    # set default options
    options = {
               '--from'      : 'Blushing Gorilla <gorilla@jungle.com>',
               '--subject'   : 'Invitation to the jungle',
               '--server'    : 'localhost:8025',
               '--parameter' : str(parm),
               '--body'      : str(body),
               }
    # options can be passed by a test as a dictionary or as a list
    # as a dictionary
    options.update(opts)
    opts = []
    for option, value in options.items():
        opts.extend((option, value))
    # we need to allow passing options as a list for those options that can be
    # passed multiple times, e.g. --attachment, where a dictionary wouldn't work
    opts.extend(opts_list)
    # now we have all default options + options passed by the test
    # instantiate a click Runner
    script = click.testing.CliRunner()
    result = script.invoke(massmail, opts, input='y\n')
    if errs:
        # we expect errors, so do not interact with the SMTP server at all
        # and read the errors from the script instead
        assert result.exit_code != 0
        return result.output
    else:
        # parse the output of the SMTP server which is running in the background
        protocol, emails = parse_smtp(server)
        # in case of unexpected error, let's print the output so we have a chance
        # to debug without touching the code here
        if result.exit_code != 0:
            print(result.output)
            print(protocol)
        assert result.exit_code == 0
        # return the protocol text and a list of emails
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

    # check that we have inserted the right values for our keys
    text = email.get_content()
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
    text = email.get_content()
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
    # we have to trust the internal email_module machinery
    # to perform the proper decoding
    text = email.get_content()
    assert 'œ´®†¥¨ˆøπ¬˚∆˙©ƒ∂ßåΩ≈ç√∫˜µ≤ユーザーコードa😀' in text

def test_unicode_subject(server, parm, body):
    opts = {'--subject' : 'Üni©ödę¿' }
    protocol, emails = cli(server, parm, body, opts=opts)
    email = emails[0]
    assert email['Subject'] == 'Üni©ödę¿'

def test_unicode_from(server, parm, body):
    opts = { '--from' : 'Üni©ödę¿ <broken@email.com>' }
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
    assert 'Dear Alice Joyce' in emails[0].get_content()
    assert 'Dear John Smith' in emails[1].get_content()

def test_unicode_parm(server, parm, body):
    # add some unicode text to the body
    with parm.open('at') as parmf:
        parmf.write('\nÜni©ödę¿; Smith; j@monkeys.com\n')
    protocol, emails = cli(server, parm, body)
    assert 'Dear Üni©ödę¿ Smith' in emails[1].get_content()

def test_multiple_recipients_in_one_row(server, parm, body):
    # add some unicode text to the body
    with parm.open('at') as parmf:
        parmf.write('\nAnne and Mary; Joyce; a@donkeys.com, m@donkeys.com\n')
    protocol, emails = cli(server, parm, body)
    assert len(emails) == 2
    assert 'sender: gorilla@jungle.com' in protocol
    assert 'recip: donkeys@jungle.com' in protocol
    assert 'recip: a@donkeys.com' in protocol
    assert 'recip: m@donkeys.com' in protocol

    assert emails[0]['To'] == 'donkeys@jungle.com'
    assert emails[1]['To'] == 'a@donkeys.com, m@donkeys.com'
    assert 'Dear Alice Joyce' in emails[0].get_content()
    assert 'Dear Anne and Mary Joyce' in emails[1].get_content()


def test_parm_malformed_keys(server, parm, body):
    parm.write_text("""$NAME;$SURNAME$;$EMAIL$
                    test;test;test@test.com""")
    output = cli(server, parm, body, errs=True)
    assert '$NAME' in output
    assert 'malformed' in output
    parm.write_text("""$NAME$;SURNAME$;$EMAIL$
                    test;test;test@test.com""")
    output = cli(server, parm, body, errs=True)
    assert 'SURNAME$' in output
    assert 'malformed' in output

def test_missing_email_in_parm(server, parm, body):
    parm.write_text("""$NAME$;$SURNAME$
                    test;test""")
    assert 'No $EMAIL$' in cli(server, parm, body, errs=True)

def test_too_many_values_in_parm(server, parm, body):
    with parm.open('at') as parmf:
        parmf.write('\nMario;Rossi;j@monkeys.com;too much\n')
    output = cli(server, parm, body, errs=True)
    assert 'Line 2' in output
    assert '4 found instead of 3' in output

def test_missing_values_in_parm(server, parm, body):
    with parm.open('at') as parmf:
        parmf.write('\nMario;j@monkeys.com\n')
    output = cli(server, parm, body, errs=True)
    assert 'Line 2' in output
    assert '2 found instead of 3' in output

def test_empty_values_in_parm(server, parm, body):
    with parm.open('at') as parmf:
        parmf.write('\nMario;;j@monkeys.com\n')
    output = cli(server, parm, body, errs=True)
    assert 'Line 2' in output
    assert 'empty value for key $SURNAME$' in output

def test_server_offline(server, parm, body):
    opts = {'--server' : 'noserver:25' }
    assert 'Can not connect to' in cli(server, parm, body, opts=opts, errs=True)

def test_server_wrong_authentication(server, parm, body):
    opts = {'--user' : 'noone', '--password' : 'nopass' }
    assert 'Can not login' in cli(server, parm, body, opts=opts, errs=True)

def test_bcc(server, parm, body):
    opts = {'--bcc' : 'x@monkeys.com'}
    protocol, emails = cli(server, parm, body, opts=opts)

    assert len(emails) == 1
    assert 'sender: gorilla@jungle.com' in protocol
    assert 'recip: donkeys@jungle.com' in protocol
    assert 'recip: x@monkeys.com' in protocol

    assert emails[0]['To'] == 'donkeys@jungle.com'
    assert 'Bcc' not in emails[0]

def test_cc(server, parm, body):
    opts = {'--cc' : 'Markus Murkis <x@monkeys.com>'}
    protocol, emails = cli(server, parm, body, opts=opts)

    assert len(emails) == 1
    assert 'sender: gorilla@jungle.com' in protocol
    assert 'recip: donkeys@jungle.com' in protocol
    assert 'recip: x@monkeys.com' in protocol

    assert emails[0]['To'] == 'donkeys@jungle.com'
    assert emails[0]['Cc'] == 'Markus Murkis <x@monkeys.com>'

def test_in_reply_to(server, parm, body):
    opts = {'--inreply-to' : '<MessageID>'}
    protocol, emails = cli(server, parm, body, opts=opts)

    assert len(emails) == 1
    assert emails[0]['In-Reply-To'] == '<MessageID>'

def test_invalid_in_reply_to(server, parm, body):
    opts = {'--inreply-to' : 'abc'}
    output = cli(server, parm, body, opts=opts, errs=True)
    assert 'Invalid value' in output
    assert 'brackets' in output

def test_validate_from(server, parm, body):
    opts = {'--from' : 'invalid@email'}
    assert 'is not a valid email' in cli(server, parm, body, opts=opts, errs=True)
    opts = {'--from' : 'Blushing Gorilla'}
    assert 'is not a valid email' in cli(server, parm, body, opts=opts, errs=True)
    opts = {'--from' : 'Blushing Gorilla <invalid@email>'}
    assert 'is not a valid email' in cli(server, parm, body, opts=opts, errs=True)

def test_invalid_email_in_parm(server, parm, body):
    with parm.open('at') as parmf:
        parmf.write('\nMario;Rossi;j@monkeys\n')
    output = cli(server, parm, body, errs=True)
    assert 'is not a valid email' in output
    assert 'Line 2' in output

def test_rich_email_address_in_parm(server, parm, body):
    with parm.open('at') as parmf:
        parmf.write('\nMario;Rossi;Mario Rossi <j@monkeys.org>\n')
    protocol, emails = cli(server, parm, body)
    assert 'recip: j@monkeys.org' in protocol
    assert 'Mario Rossi' in emails[1]['To']
    assert 'j@monkeys.org' in emails[1]['To']

def test_attach_png_and_pdf(server, parm, body, tmp_path):
    # create a little PNG (greyscale, 1x1 pixel) from:
    # https://garethrees.org/2007/11/14/pngcrush/
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x00\x00\x00\x007n\xf9$\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
    png_file = tmp_path / 'test.png'
    png_file.write_bytes(png_bytes)

    # create a little PDF (stackoverflow + adaptations)
    pdf_bytes = b"%PDF-1.2 \n9 0 obj\n<<\n>>\nstream\nBT/ 32 Tf(text)' ET\nendstream\nendobj\n4 0 obj\n<<\n/Type /Page\n/Parent 5 0 R\n/Contents 9 0 R\n>>\nendobj\n5 0 obj\n<<\n/Kids [4 0 R ]\n/Count 1\n/Type /Pages\n/MediaBox [ 0 0 250 50 ]\n>>\nendobj\n3 0 obj\n<<\n/Pages 5 0 R\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 3 0 R\n>>\n%%EOF"
    pdf_file = tmp_path / 'test.pdf'
    pdf_file.write_bytes(pdf_bytes)

    opts = ('--attachment', str(png_file), '--attachment', str(pdf_file))
    protocol, emails = cli(server, parm, body, opts_list=opts)
    email = emails[0]
    assert 'Dear Alice Joyce' in email.get_body().get_content()
    attachments = list(email.iter_attachments())
    assert attachments[0].get_content_type() == 'image/png'
    assert attachments[0].get_filename() == 'test.png'
    assert attachments[0].get_content() == png_bytes
    assert attachments[1].get_content_type() == 'application/pdf'
    assert attachments[1].get_filename() == 'test.pdf'
    assert attachments[1].get_content() == pdf_bytes

def test_unknown_attachment_type(server, parm, body, tmp_path):
    random_bytes = b'\x9diou\xd5\x12\xdf/\x03\xf8'
    fl = tmp_path / 'dummy'
    fl.write_bytes(random_bytes)

    opts = {'--attachment' : str(fl)}
    protocol, emails = cli(server, parm, body, opts=opts)
    attachments = list(emails[0].iter_attachments())
    assert attachments[0].get_content_type() == 'application/octet-stream'
    assert attachments[0].get_content() == random_bytes
