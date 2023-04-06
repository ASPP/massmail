import contextlib
import email
import io
import sys
import os
import time
import subprocess
import base64
import tempfile

import massmail.massmail as massmail

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
    server = subprocess.Popen([sys.executable,
                               '-m', 'aiosmtpd',
                               '-n',
                               '-d',
                               '-l',  address,
                               '-c', 'aiosmtpd.handlers.Debugging', 'stderr'],
                              stdin=None,
                              text=False,
                              stderr=subprocess.PIPE,
                              stdout=None,
                              bufsize=0)
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
        # we should find a Date header and a message-id header in the email
        # we can't replicate them here, so get rid of them before comparing
        generated_lines = msgs['testrecv@test.org'].as_string().splitlines()
        generated = []
        found_date = False
        found_messageid = False
        for line in generated_lines:
            if line.startswith('Date:'):
                found_date = True
            elif line.startswith('Message-ID:'):
                found_messageid = True
            else:
                generated.append(line)
        assert found_date
        assert found_messageid
        assert  generated == expected_email.as_string().splitlines()

def test_fake_sending():
    address = 'localhost:8025'
    with tempfile.NamedTemporaryFile('wt') as f:
        f.write('$EMAIL$;$VALUE$\ntestrecv@test;this is a test\n')
        f.flush()
        with fake_smtp_server(address) as server:
            with replace_stdin('EMAIL=$EMAIL$\nVALUE=$VALUE$\n'):
                massmail.main(['-F', 'fake@foobar.com',
                                '-z', address, '-f', '-t',
                                f.name])

    stderr = server.stderr.read()
    assert b'sender: fake@foobar.com' in stderr
    assert b'recip: testrecv@test' in stderr

    encoded = base64.b64encode(b'EMAIL=testrecv@test\nVALUE=this is a test\n')
    assert encoded in stderr
