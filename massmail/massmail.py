import email
import mimetypes
import pathlib
import re
import smtplib

import click
import email_validator


def parse_parameter_file(parameter_file):
    name = parameter_file.name
    pars = parameter_file.read()
    pars = pars.splitlines()

    # get keywords from first line
    key_list = [key.strip() for key in pars[0].split(';')]

    # fail immediately if no EMAIL keyword is found
    if '$EMAIL$' not in key_list:
        raise click.ClickException(f'No $EMAIL$ keyword found in {name}')

    # check that all keywords start and finish with a '$' character
    for key in key_list:
        if not key.startswith('$') or not key.endswith('$'):
            raise click.ClickException(f'Keyword {key=} malformed in {name}: should be $KEY$')

    # gather all values
    keys = dict([(key, []) for key in key_list])
    for count, line in enumerate(pars[1:]):
        # ignore empty lines
        if len(line) == 0:
            continue
        values = [key.strip() for key in line.split(';')]
        if len(values) != len(key_list):
            raise click.ClickException(f'Line {count+1} in {name} malformed: '
                             f'{len(values)} found instead of {len(key_list)}')
        for i, key in enumerate(key_list):
            keys[key].append(values[i])

    # validate email addresses
    for idx, emails in enumerate(keys['$EMAIL$']):
        # split into individual email addresses
        validated = []
        for email in emails.split(','):
            # remove spaces
            email = email.strip()
            validated.append(validate_email_address(email,
                                        errstr=f'Line {idx+1} in {name}:\n'))
        # store the validated and normalized email addresses back into the dict
        keys['$EMAIL$'][idx] = ','.join(validated)
    return keys

def create_email_bodies(body_file, keys, fromh, subject, cc, bcc, inreply_to, attachment):
    msgs = {}
    body_text = body_file.read()

    # collect attachments once and then attach them to every single message
    attachments = {}
    for path in attachment:
        # guess the MIME type based on file extension only...
        mime, encoding = mimetypes.guess_type(path, strict=False)
        # if no guess or if the type is already encoded, the MIME type is octet-stream
        if mime is None or encoding is not None:
            mime = 'application/octet-stream'
        maintype, subtype = mime.split('/', 1)
        data = path.read_bytes()
        attachments[path.name] = (data, maintype, subtype)

    for i, emails in enumerate(keys['$EMAIL$']):
        # find keywords and substitute with values
        body = re.sub(r'\$\w+\$', lambda m: keys[m.group(0)][i], body_text)
        msg = email.message.EmailMessage()
        msg.set_content(body)
        msg['To'] = emails
        msg['From'] = fromh
        msg['Subject'] = subject
        if inreply_to:
            msg['In-Reply-To'] = inreply_to
        if cc:
            msg['Cc'] = cc
        if bcc:
            msg['Bcc'] = bcc
        # add the required date header
        msg['Date'] = email.utils.localtime()
        # add a unique message-id
        msg['Message-ID'] = email.utils.make_msgid()
        # add attachments
        for name, (data, mtyp, styp) in attachments.items():
            msg.add_attachment(data, filename=name, maintype=mtyp, subtype=styp)
        msgs[emails] = msg

    return msgs

def send_messages(msgs, force, server, tls, user, password):
    for emailaddr in msgs:
        emails = [e.strip() for e in emailaddr.split(',')]
        print('This email will be sent to:', ', '.join(emails))
        for hdr, value in msgs[emailaddr].items():
            print(f'{hdr}: {value}')
        for attachment in msgs[emailaddr].iter_attachments():
            name = attachment.get_filename()
            content_type = attachment.get_content_type()
            print(f'Attachment ({content_type}): {name}')
        body = msgs[emailaddr].get_body().get_content()
        print(f'\n{body}')

    if not force:
        # ask for confirmation before really sending stuff
        if not click.confirm('Send the emails above?', default=None):
            raise click.ClickException('Aborted! We did not send anything!')

        print()

    servername = server.split(':')[0]
    try:
        server = smtplib.SMTP(server)
    except Exception as err:
        raise click.ClickException(f'Can not connect to "{servername}": {err}')

    if tls:
        server.starttls()

    if user is not None:
        try:
            # get password if needed
            if password is None:
                password = click.prompt(f'Enter password for {user} on {servername}',
                                    hide_input=True)
            server.login(user, password)
        except Exception as err:
            raise click.ClickException(f'Can not login to {servername}: {err}')

    print()

    for emailaddr in msgs:
        print('Sending email to:', emailaddr)
        try:
            out = server.send_message(msgs[emailaddr])
        except Exception as err:
            raise click.ClickException(f'Can not send email: {err}')

        if len(out) != 0:
            raise click.ClickException(f'Can not send email: {err}')

    server.quit()

def validate_inreply_to(context, param, value):
    if value is None:
        return None
    if not (value.startswith('<') and value.endswith('>')):
        raise click.BadParameter(f"must be enclosed in brackets (<MESSAGE-ID>): {value}!")
    return value

def validate_email_address(value, errstr=''):
    # we support two kind of email address:
    # 1. x@y.org
    # 2. Blushing Gorilla <x@y.org>
    if address := re.match(r'(.+)<(\S+)>', value):
        # we are dealing with form 2
        # extract the email address
        prefix = address.group(1) # here we get "Blushing Gorilla "
        address = address.group(2) # here we get x@y.org
    else:
        # we are dealing with form 1
        prefix = None
        address = value
    # validate the email address
    try:
        emailinfo = email_validator.validate_email(address, check_deliverability=False)
    except email_validator.EmailNotValidError as e:
        raise click.BadParameter(errstr+f"{value!r} is not a valid email address:\n{str(e)}")
    # support different versions of email-validator
    try:
        email = emailinfo.normalized # version >= 2.0
    except AttributeError:
        email = emailinfo.email # version <= 1.3
    if prefix:
        return f'{prefix}<{email}>'
    else:
        return email


# a custom click parameter type to represent email addresses
class Email(click.ParamType):
    name = "Email"

    def convert(self, value, param, ctx):
        # validate the email address
        try:
            return validate_email_address(value)
        except click.BadParameter as e:
            self.fail(str(e), param, ctx)

@click.command(context_settings={'help_option_names': ['-h', '--help'],
                                 'max_content_width': 120})

### REQUIRED OPTIONS ###
@click.option('-F', '--from', 'fromh', required=True, type=Email(), help='set the From: header')
@click.option('-S', '--subject', required=True, help='set the Subject: header')
@click.option('-Z', '--server', required=True, help='the SMTP server to use')
@click.option('-P', '--parameter', 'parameter_file', required=True,
              type=click.File(mode='rt', encoding='utf8', errors='strict'),
              help='set the parameter file (see above for an example)')
@click.option('-B', '--body', 'body_file', required=True,
              type=click.File(mode='rt', encoding='utf8', errors='strict'),
              help='set the email body file (see above for an example)')

### OPTIONALS ###
@click.option('-b', '--bcc', type=Email(), help='set the Bcc: header')
@click.option('-c', '--cc', type=Email(), help='set the Cc: header')
@click.option('-r', '--inreply-to', callback=validate_inreply_to, metavar="<ID>",
              help='set the In-Reply-to: header. Set it to a Message-ID.')
@click.option('-u', '--user', help='SMTP user name. If not set, use anonymous SMTP connection')
@click.option('-p', '--password', help='SMTP password. If not set you will be prompted for one')
@click.option('-a', '--attachment', help='add attachment [repeat for multiple attachments]',
              multiple=True, type=click.Path(exists=True, dir_okay=False,
                                             readable=True, path_type=pathlib.Path))

### INTERNAL OPTIONS ###
# do not ask for confirmation before sending messages (to be used in tests)
@click.option('-f', '--force', is_flag=True, default=False, hidden=True)
# do not TLS encrypt connection to SMTP server (to be used in tests)
@click.option('--tls/--no-tls', default=True, hidden=True)

### MAIN SCRIPT ###
def main(fromh, subject, server, parameter_file, body_file, bcc, cc, inreply_to,
         user, password, attachment, force, tls):
    """Send mass mail

    Example:

     \b
     massmail --from "Blushing Gorilla <gorilla@jungle.com>" --subject "Invitation to the jungle" --server mail.example.com:587 --user user@example.com -P parm.csv -B body.txt

    parm.csv (semi-colon separated):

     \b
     $NAME$; $SURNAME$; $EMAIL$
     John; Smith; j@monkeys.com
     Anne and Mary; Joyce; a@donkeys.com, m@donkeys.com

    body.txt:

     \b
     Dear $NAME$ $SURNAME$,
     we kindly invite you to join us in the jungle
     Cheers,
     Gorilla

    Notes:

      Values from the parameter file (parm.csv) are inserted in the body text (body.txt). The keyword $EMAIL$ must always be present in the parameter files and contains a comma separated list of email addresses. Keep in mind shell escaping when setting headers with white spaces or special characters. Both files must be UTF8 encoded!
    """
    keys = parse_parameter_file(parameter_file)
    msgs = create_email_bodies(body_file, keys, fromh, subject, cc, bcc, inreply_to, attachment)
    send_messages(msgs, force, server, tls, user, password)

