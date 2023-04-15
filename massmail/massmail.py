import email
import re
import smtplib

import click


def parse_parameter_file(parameter_file, separator):
    name = parameter_file.name
    pars = parameter_file.read()
    pars = pars.splitlines()

    # get keywords from first line
    key_list = [key.strip() for key in pars[0].split(separator)]

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
        values = [key.strip() for key in line.split(separator)]
        if len(values) != len(key_list):
            raise click.ClickException(f'Line {count+1} in {name} malformed: '
                             f'{len(values)} found instead of {len(key_list)}')
        for i, key in enumerate(key_list):
            keys[key].append(values[i])

    return keys

def create_email_bodies(body_file, keys, fromh, subject, cc, bcc, reply_to):
    msgs = {}
    body_text = body_file.read()
    for i, emails in enumerate(keys['$EMAIL$']):
        # find keywords and substitute with values
        body = re.sub(r'\$\w+\$', lambda m: keys[m.group(0)][i], body_text)
        msg = email.message.EmailMessage()
        msg.set_content(body)
        msg['To'] = emails
        msg['From'] = fromh
        msg['Subject'] = subject
        if reply_to:
            msg['In-Reply-To'] = reply_to
        if cc:
            msg['Cc'] = cc
        if bcc:
            msg['Bcc'] = bcc
        # add the required date header
        msg['Date'] = email.utils.localtime()
        # add a unique message-id
        msg['Message-ID'] = email.utils.make_msgid()
        msgs[emails] = msg

    return msgs

def send_messages(msgs, force, server, tls, smtpuser, smtppassword):
    for emailaddr in msgs:
        emails = [e.strip() for e in emailaddr.split(',')]
        print('This email will be sent to:', ', '.join(emails))
        [print(hdr+':', value) for hdr, value in msgs[emailaddr].items()]
        print()
        print(msgs[emailaddr].get_payload())

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

    if smtpuser is not None:
        try:
            # get password if needed
            if smtppassword is None:
                smtppassword = click.prompt(f'Enter password for {smtpuser} on {servername}',
                                    hide_input=True)
            server.login(smtpuser, smtppassword)
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


def validate_separator(context, param, value):
    # only one single character is allowedm and it can not be a comma [because we
    # want to use a comma separated list in the $EMAIL$ parameter]
    if len(value) > 1 or value == ',':
        raise click.BadParameter(f"only once char different from comma is permitted: '{value}'!")
    return value

def validate_reply_to(context, param, value):
    if value is None:
        return None
    if not (value.startswith('<') and value.endswith('>')):
        raise click.BadParameter(f"must be enclosed in brackets (<MESSAGE-ID>): {value}!")
    return value

@click.command(context_settings={'help_option_names': ['-h', '--help'],
                                 'max_content_width': 120})
@click.option('-F', '--from', 'fromh', required=True, help='set the From: header')
@click.option('-S', '--subject', required=True, help='set the Subject: header')
@click.option('-Z', '--server', required=True, help='the SMTP server to use')
@click.option('-P', '--parameter', 'parameter_file', required=True,
              type=click.File(mode='rt', encoding='utf8', errors='strict'),
              help='set the parameter file (see above for an example)')
@click.option('-B', '--body', 'body_file', required=True,
              type=click.File(mode='rt', encoding='utf8', errors='strict'),
              help='set the email body file (see above for an example)')
@click.option('-b', '--bcc', help='set the Bcc: header')
@click.option('-c', '--cc', help='set the Cc: header')
@click.option('-r', '--reply-to', callback=validate_reply_to, metavar="<ID>",
              help='set the In-Reply-to: header. Set it to a Message-ID.')
@click.option('-u', '--smtpuser', help='SMTP user name. If not set, use anonymous SMTP connection')
@click.option('-p', '--smtppassword', help='SMTP password. If not set you will be prompted for one')
@click.option('-f', '--force', is_flag=True, default=False, help='do not ask for confirmation before sending messages (use with care!)')
@click.option('--tls/--no-tls', default=True, show_default=True,
              help='encrypt SMTP connection with TLS (disable only if you know what you are doing!)')
@click.option('--separator', help='set field separator in parameter file [comma "," is not permitted]',
              default=';', show_default=True, callback=validate_separator, metavar="CHAR")
def main(fromh, subject, server, parameter_file, body_file, bcc, cc, reply_to,
         smtpuser, smtppassword, force, tls, separator):
    """Send mass mail

    Example:

     \b
     massmail --from "Blushing Gorilla <gorilla@jungle.com>" --subject "Invitation to the jungle" --server smtp.gmail.com:587 -P parm.csv -B body.txt

    parm.csv:

     \b
     $NAME$; $SURNAME$; $EMAIL$
     John; Smith; j@monkeys.com
     Anne; Joyce; a@donkeys.com

    body.txt:

     \b
     Dear $NAME$ $SURNAME$,
     we kindly invite you to join us in the jungle
     Cheers,
     Gorilla

    Notes:

      Keywords from the parameter file (parm.csv) are subsituted in the body text. The keyword $EMAIL$ must always be present in the parameter files and contains a comma separated list of email addresses. Keep in mind shell escaping when setting headers with white spaces or special characters. Both files must be UTF8 encoded!
    """
    keys = parse_parameter_file(parameter_file, separator)
    msgs = create_email_bodies(body_file, keys, fromh, subject, cc, bcc, reply_to)
    send_messages(msgs, force, server, tls, smtpuser, smtppassword)

