import re
import smtplib
import sys
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from string import Template
from time import sleep
import keyring
import pandas as pd
import click

click.clear()
service_id = 'MAILSEND'


def extract_names(temp, in_cols):
    found = set()
    for match in Template.pattern.finditer(temp.template):
        name = match.group('named') or match.group('braced')
        if name is not None and name in in_cols:
            found.add(name)
    return found


def extract_file_data(fname, only_cols=False):
    df = pd.read_csv(fname)
    cols = set(df.columns.values)
    if only_cols:
        return cols
    return df, cols


def format_text(msg, df, add_file, in_cols):
    msg = Template(msg)
    var_dict = dict()
    with open(add_file, 'r') as afile:
        add_list = [add.strip() for add in afile.readlines()]
    names = extract_names(msg, in_cols)
    for i, address in enumerate(add_list):
        for name in names:
            var_dict[name] = df[name][i]
        yield address, msg.safe_substitute(var_dict)


def create_mail(msg, sender, target, sub, attach):
    message = MIMEMultipart()
    message['From'] = sender
    message['To'] = target
    message['Subject'] = sub
    message.attach(MIMEText(msg, 'plain'))
    if attach:
        with open(attach, 'r') as atfile:
            at = MIMEBase('application', 'octate-stream')
            at.set_payload(atfile.read())
            encoders.encode_base64(at)
        message.attach(at)
    return message.as_string()


def write_mail(fname, add_file, email_id, passwd, attach):
    srv = smtplib.SMTP('smtp.gmail.com', 587)
    confirm = True
    try:
        click.clear()
        click.echo('please enter the message to be sent \n')
        msg = sys.stdin.readlines()
        msg = ''.join([line for line in msg])
        sub = click.prompt('enter subject for email \n>> ')

        srv.starttls()
        srv.login(email_id, passwd)
        if fname:
            df, cols = extract_file_data(fname)
            for address, body in format_text(msg, df, add_file, cols):
                if confirm:
                    click.echo(body)
                    if click.confirm('are you sure you want to proceed with this email?'):
                        confirm = False
                    else:
                        sys.exit('Aborted!')
                srv.sendmail(email_id, address, create_mail(
                    body, email_id, address, sub, attach))
                sleep(1.0)
            else:
                with open(add_file, 'r') as afile:
                    add_list = [add.strip() for add in afile.readlines()]
                for address in add_list:
                    srv.sendmail(email_id, address, create_mail(
                        msg, email_id, address, sub, attach))

    finally:
        srv.quit()


@click.command()
@click.argument('target_file', type=click.Path(exists=True))
@click.option('fname', '--fname', '-f', type=click.Path(exists=True))
@click.option('--attach', '-a', 'attach', type=click.Path(exists=True))
def cli_face(target_file, fname, attach):
    click.echo(click.style('''
                    _ __                    __
   ____ ___  ____ _(_) /_______  ____  ____/ /
  / __ `__ \/ __ `/ / / ___/ _ \/ __ \/ __  / 
 / / / / / / /_/ / / (__  )  __/ / / / /_/ /  
/_/ /_/ /_/\__,_/_/_/____/\___/_/ /_/\__,_/   
                                              
''', fg='green'))
    click.echo('welcome to mailsend!')
    click.echo('written by Devansh Joshi')
    click.echo("you may need google app passwords to run this script read about them here- https://support.google.com/accounts/answer/185833?hl=en")
    click.echo()
    email_pat = re.compile('\w+@\w+\.[a-z]+', re.ASCII)
    while True:
        email_id = click.prompt('enter the email id \n>> ')
        passwd = keyring.get_password(service_id, email_id)

        if passwd:
            if click.prompt('enter del to delete the mail and password, anything else to proceed \n>> ').lower() == 'del':
                keyring.delete_password(service_id, email_id)
                click.clear()
                continue
            write_mail(fname=fname, add_file=target_file,
                       email_id=email_id, passwd=passwd, attach=attach)
            click.echo('mailed successfully!')
            sys.exit()
        elif email_pat.match(email_id):
            keyring.set_password(service_id, email_id, click.prompt(
                'new email id? enter password \n>> '))
        else:
            click.clear()
            click.echo('invalid input')


try:
    cli_face()
except smtplib.SMTPAuthenticationError:
    click.echo('Please check the username and password entered!')
except TypeError:
    click.echo(
        'one or both of the files seem to be the wrong type, please check them again')
