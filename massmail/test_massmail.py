import tempfile

import massmail.massmail as massmail

def test_dummy():
    pass

def test_command_help():
    import pytest
    with pytest.raises(SystemExit):
        massmail.main(['-h'])

def test_parse_parameter_file():
    expected_keywords = {u'$VALUE$': [u'this is a test'], u'$EMAIL$': [u'testrecv@test']}
    with tempfile.NamedTemporaryFile('wt') as f:
        f.write('$EMAIL$;$VALUE$\ntestrecv@test;this is a test')
        f.flush()
        cmd_options = [
            '-F', 'testfrom@test',
            '-z', 'localhost',
            f.name,
        ]
        options = massmail.parse_command_line_options(cmd_options)
        keywords, email_count = massmail.parse_parameter_file(options)
    assert keywords == expected_keywords
