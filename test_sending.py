import contextlib
import email
import io
import sys
import os
import time
import subprocess
import base64
import tempfile

import massmail

@contextlib.contextmanager
def replace_stdin(text):
    input = io.StringIO(text)
    old = sys.stdin
    sys.stdin, old = input, sys.stdin
    try:
        yield
    finally:
        sys.stdin = old

@contextlib.contextmanager
def fake_smtp_server(address):
    devnull = open(os.devnull, 'w')
    server = subprocess.Popen(['python2',
                               '-m', 'smtpd',
                               '-n',
                               '-d',
                               '-c', 'DebuggingServer',
                               address],
                              stdin=devnull,
                              stdout=devnull,
                              stderr=subprocess.PIPE)
    try:
        time.sleep(1)
        yield server
    finally:
        server.terminate()

def test_local_sending():
    parameter_string = '$EMAIL$;$NAME$;$VALUE$\ntestrecv@test.org;TestName;531'
    email_body = 'Dear $NAME$,\nthis is a test: $VALUE$\nBest regards'
    email_to = 'testrecv@test.org'
    email_from = 'testfrom@test.org'
    email_subject = 'Test Subject'
    email_encoding = 'utf-8'

    expected_email = email.mime.text.MIMEText('Dear TestName,\nthis is a test: 531\nBest regards'.encode(email_encoding), 'plain', email_encoding)
    expected_email['To'] = email_to
    expected_email['From'] = email_from
    expected_email['Subject'] = email.header.Header(email_subject.encode(email_encoding), email_encoding)

    with tempfile.NamedTemporaryFile('wt') as f:
        f.write(parameter_string)
        f.flush()
        cmd_options = [
            '-F', email_from,
            '-S', email_subject,
            '-z', 'localhost',
            '-e', email_encoding,
            f.name
        ]
        options = massmail.parse_command_line_options(cmd_options)
        keywords, email_count = massmail.parse_parameter_file(options)
        msgs = massmail.create_email_bodies(options, keywords, email_count, email_body)
        massmail.add_email_headers(options, msgs)
        assert msgs['testrecv@test.org'].as_string() == expected_email.as_string()

def test_sending_fake_address():
    address = 'localhost:1025'
    with tempfile.NamedTemporaryFile('wt') as f:
        f.write('$EMAIL$;$VALUE$\ntestrecv@test;this is a test')
        f.flush()

        with fake_smtp_server(address) as server:
            with replace_stdin('EMAIL=$EMAIL$\nVALUE=$VALUE$'):
                massmail.main(['-F', 'fake@foobar.com',
                               '-z', address, '-s', True,
                               f.name])

    output = server.stderr.read()
    assert b'MAIL FROM:<fake@foobar.com>' in output
    assert b'RCPT TO:<testrecv@test>' in output

    encoded = base64.b64encode(b'EMAIL=testrecv@test\nVALUE=this is a test')
    assert encoded in output
