This is a package for sending mass emails.

Usage:
  %s [...] PARAMETER_FILE < BODY

Options:
  -F FROM           set the From: header for all messages.
                    Must be ASCII. This argument is required

  -S SUBJECT        set the Subject: header for all messages

  -B BCC            set the Bcc: header for all messages.
                    Must be ASCII

  -R In-Reply-To    set the In-Reply-To: takes a Message-ID as input

  -s SEPARATOR      set field separator in parameter file,
                    default: ";"

  -e ENCODING       set PARAMETER_FILE *and* BODY character set
                    encoding, default: "UTF-8". Note that if you fuck
                    up this one, your email will be full of rubbish:
                    You have been warned!

  -f                fake run: don't really send emails, just print to
                    standard output what would be done. Don't be scared
                    if you can not read the body: it is base64 encoded
                    UTF8 text

  -z SERVER         the SMTP server to use. This argument is required

  -P PORT           the SMTP port to use. Must be between 1 and 65535.

  -u                SMTP user name. If not set, use anonymous SMTP
                    connection

  -p                SMTP password. If not set you will be prompted for one

  -h                show this usage message

Notes:
  The message body is read from standard input or
  typed in interactively (exit with ^D) and keywords are subsituted with values
  read from a parameter file. The first line of the parameter file defines
  the keywords. The keyword $EMAIL$ must always be present and contains a comma
  separated list of email addresses.
  Keep in mind shell escaping when setting headers with white spaces or special
  characters.
  Character set encodings are those supported by python.

Examples:

* Example of a parameter file:

$NAME$; $SURNAME$; $EMAIL$
John; Smith; j@guys.com
Anne; Joyce; a@girls.com

* Example of body:

Dear $NAME$ $SURNAME$,

I think you are a great guy/girl!

Cheers,

My self.

* Example usage:

%s  -F "Great Guy <gg@guys.com>" -S "You are a great guy" -B "Not so great Guy <ngg@guys.com>" parameter-file < body