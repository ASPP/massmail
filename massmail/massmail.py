#!/usr/bin/env python3
import collections
import csv
import email
import mimetypes
import pathlib
import re
import smtplib

import rich.prompt
import rich.panel
import rich.progress
from rich import print as rprint
import click
import email_validator


def parse_parameter_file(parameter_file, delimiter=None):
    name = parameter_file.name
    # sniff the CSV dialect, so that we can support different CSV formats
    # note: the newline argument is important, or the dialect sniffing does not work properly
    # always assume UTF8
    parm = parameter_file.open('rt', encoding='utf8', errors='strict', newline='')
    if delimiter is None:
        try:
            dialect = csv.Sniffer().sniff(parm.read())
            reader_opts = {'dialect' : dialect}
            parm.seek(0)
        except csv.Error as exc:
            raise click.BadParameter(f'Could not automatically guess CSV format, please specify the deilimiter with -d!')
    else:
        reader_opts = {'delimiter' : delimiter}
    reader = csv.DictReader(parm, **reader_opts) #delimiter=';')

    # fail immediately if no EMAIL keyword is found
    if '$EMAIL$' not in reader.fieldnames:
        raise click.ClickException(f'No $EMAIL$ keyword found in {name}')

    # check that all keywords start and finish with a '$' character
    for key in reader.fieldnames:
        if not key.startswith('$') or not key.endswith('$'):
            raise click.ClickException(f'Keyword {key=} malformed in {name}: should be $KEY$')

    keys = collections.defaultdict(list)
    for count, row in enumerate(reader):
        errstr = f'Line {count+2} in {name} malformed'
        # verify that we don't have too many values
        if None in row:
            raise click.ClickException(f'{errstr}: {len(row.values())} found instead of {len(reader.fieldnames)}')
        # verify that we are not missing values
        if None in row.values():
            values = list(row.values())
            values.remove(None)
            raise click.ClickException(f'{errstr}: {len(values)} found instead of {len(reader.fieldnames)}')
        for key, value in row.items():
            value_str = value.strip()
            # validate email addresses
            if key == '$EMAIL$':
                validated_emails = [validate_email_address(email.strip(), errstr) for email in value_str.split(',')]
                value_str = ','.join(validated_emails)
            keys[key].append(value_str)

    # return a normal dict, and not a defaultdict, so that access to unknown keys later
    # in the code throw the appropriate KeyError instead of returning an empty list
    return dict(keys)


def create_email_bodies(body_file, keys, fromh, subject, cc, bcc, inreply_to, attachment):
    msgs = {}
    body_text = body_file.read()
    warned_once = False
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

        # The following line does this:
        # - Assume that the parameter file has an header like
        #     $NAME$;$SURNAME$;$EMAIL$
        # - Assume that line "i" from the parameter file look like this
        #     Gorilla; Blushing; email@gorillas.org
        # - Then the following like is equivalent to having a loop over the keys
        #   from the parameter file: ($NAME$, $SURNAME$)
        # - The m in the lambda is going to be the re.match object for $NAME$ at the
        #   first iteration, and the re.match object for $SURNAME$ at the second one
        # - at every iteration, m.group(0) is the string of the matching key, i.e.
        #   it is "$NAME$" at the first iteration and "$SURNAME$" at the second one
        # - keys[m.group(0)] is then equivalent, at the first iteration, to
        #     keys["$NAME$"] == ["Gorilla", "Othername1", "Othername2"]
        # - keys[.group(0)][i] is then equivalent, at the first iteration, to
        #     keys["$NAME$"][i] == "Gorilla"
        #   if we assume that "Gorilla" is on line i
        # - at the second iteration, we will have:
        #   keys[m.group(0)] == keys["$SURNAME$"] == ["Blushing", "Othersurname1",....]
        #   keys[m.group(0)][i] = keys["$SURNAME$"][i] == "Blushing"
        # - we only have two iterations for re.sub, because we only have two keys
        #   in the body matching the regexp r'\$\w+\$'
        # - so at the end all the values corresponding to the keys will be inserted
        #   into the body_text in place of the key
        # - at the next iteration of i, we are going to select a different line from
        #   the parameter file, and generate a new email with different substitutions
        try:
            body = re.sub(r'\$\w+\$', lambda m: keys[m.group(0)][i], body_text)
        except KeyError as err:
            # an unknown key was detected
            raise click.ClickException(f'Unknown key in body file {body_file.name}: {err}')
        # warn if no keys were found
        if body == body_text and not warned_once:
            rprint(f'[bold][red]WARNING:[/red] no keys found in body file {body_file.name}[/bold]')
            warned_once = True

        msg = email.message.EmailMessage()
        try:
            # check if the body is pure ASCII
            body.encode('ascii')
            # then pass it as is to the email module machinery
            msg.set_content(body)
        except UnicodeEncodeError:
            # force CTE to be base64, so that we do not incur into strange unicode bugs
            # like for example:
            # https://github.com/python/cpython/issues/105285
            msg.set_content(body, charset='utf-8', cte='base64')
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

def send_messages(msgs, server, user, password):
    # print one example email for confirmation
    ex_addr = list(msgs.keys())[0]
    msg = msgs[ex_addr]
    panel = []
    for hdr, value in msg.items():
        if hdr in ('From', 'Subject', 'Cc', 'Bcc', 'In-Reply-To'):
            panel.append(f'[yellow]{hdr}[/yellow]: [red bold]{value}[/red bold]')
        else:
            panel.append(f'[yellow]{hdr}[/yellow]: {value}')
    for attachment in msg.iter_attachments():
        name = attachment.get_filename()
        content_type = attachment.get_content_type()
        panel.append(f'[magenta]Attachment[/magenta] ([cyan]{content_type}[/cyan]): {name}')
    body = msg.get_body().get_content()
    panel.append(f'\n{body}')
    rprint(rich.panel.Panel.fit('\n'.join(panel)))

    # ask for confirmation before really sending stuff
    rprint(f'[bold]About to send {len(msgs)} email messages like the one above…[/bold]')
    if not rich.prompt.Confirm.ask(f'[bold]Send?[/bold]'):
        #if not click.confirm('Send the emails above?', default=None):
        raise click.ClickException('Aborted! We did not send anything!')

    print()

    servername = server.split(':')[0]
    try:
        server = smtplib.SMTP(server)
    except Exception as err:
        raise click.ClickException(f'Can not connect to "{servername}": {err}')

    try:
        server.starttls()
    except Exception as err:
        raise click.ClickException(f'Could not STARTTLS with "{servername}": {err}')

    if user is not None:
        try:
            # get password if needed
            if password is None:
                password = rich.prompt.Prompt.ask(f'Enter password for '
                                                  f'[bold]{user}[/bold] '
                                                  f'on [bold]{servername}[/bold]',
                                                  password=True)
            server.login(user, password)
        except Exception as err:
            raise click.ClickException(f'Can not login to {servername}: {err}')

    print()

    for emailaddr in rich.progress.track(msgs, description="[green]Sending:[/green]"):
        rprint(f'Sending to: [bold]{emailaddr}[/bold]')
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

def validate_email_address(email, errstr=''):
    # we support two kind of email address:
    # 1. x@y.org
    # 2. Blushing Gorilla <x@y.org>
    try:
        emailinfo = email_validator.validate_email(email,
                                                   check_deliverability=False,
                                                   allow_display_name=True)
    except email_validator.EmailNotValidError as e:
        raise click.BadParameter(errstr+f"{email!r} is not a valid email address:\n{str(e)}")
    email = emailinfo.normalized
    if emailinfo.display_name:
        # always quote display_name so we support UTF8 chars in it out of the box
        return f'"{emailinfo.display_name}" <{email}>'
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
              type=click.Path(exists=True, dir_okay=False, allow_dash=True, path_type=pathlib.Path),
              #type=click.File(mode='rt', encoding='utf8', errors='strict', newline=''),
              help='set the parameter file (see above for an example)')
@click.option('-B', '--body', 'body_file', required=True,
              type=click.File(mode='rt', encoding='utf8', errors='strict'),
              help='set the email body file (see above for an example)')

### OPTIONALS ###
@click.option('-b', '--bcc', type=Email(), help='set the Bcc: header')
@click.option('-c', '--cc', type=Email(), help='set the Cc: header')
@click.option('-d', '--delimiter', type=str, default=None, help='set the delimiter for the CSV file')
@click.option('-r', '--inreply-to', callback=validate_inreply_to, metavar="<ID>",
              help='set the In-Reply-to: header. Set it to a Message-ID.')
@click.option('-u', '--user', help='SMTP user name. If not set, use anonymous SMTP connection')
@click.option('-p', '--password', help='SMTP password. If not set you will be prompted for one')
@click.option('-a', '--attachment', help='add attachment [repeat for multiple attachments]',
              multiple=True, type=click.Path(exists=True, dir_okay=False,
                                             readable=True, path_type=pathlib.Path))

### MAIN SCRIPT ###
def main(fromh, subject, server, parameter_file, body_file, bcc, cc, delimiter, inreply_to,
         user, password, attachment):
    """Send mass mail

    Example:

     \b
     massmail --from "Blushing Gorilla <gorilla@jungle.com>" --subject "Invitation to the jungle" --server mail.example.com:587 --user user@example.com -P parm.csv -B body.txt

    parm.csv:

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
    keys = parse_parameter_file(parameter_file, delimiter)
    msgs = create_email_bodies(body_file, keys, fromh, subject, cc, bcc, inreply_to, attachment)
    send_messages(msgs, server, user, password)

