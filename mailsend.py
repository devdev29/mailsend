from typing import Generator
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


def extract_names(temp: Template, in_cols: list) -> set:
    found = set()
    for match in Template.pattern.finditer(temp.template):
        name = match.group('named') or match.group('braced')
        if name is not None and name in in_cols:
            found.add(name)
    return found


def extract_file_data(fname: str) -> tuple:
    df = pd.read_csv(fname)
    cols = set(df.columns.values)
    return df, cols


def format_text(msg: str, df: pd.DataFrame, add_file: str, in_cols: list) -> Generator[tuple, None, None]:
    msg = Template(msg)
    var_dict = dict()
    with open(add_file, 'r') as afile:
        add_list = [add.strip() for add in afile.readlines()]
    names = extract_names(msg, in_cols)
    for i, address in enumerate(add_list):
        for name in names:
            var_dict[name] = df[name][i]
        yield address, msg.safe_substitute(var_dict)


def create_mail(msg: str, sender: str, target: str, sub: str, attach: str) -> str:
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


def write_mail(fname: str, add_file: str, email_id: str, passwd: str, attach: str) -> None:
    srv = smtplib.SMTP('smtp.gmail.com', 587)
    confirm = True
    try:
        if fname:
            click.clear()
            click.echo('please enter the message to be sent \n')
            msg = sys.stdin.readlines()
            msg = ''.join([line for line in msg])
            sub = click.prompt('enter subject for email \n',
                               prompt_suffix='>> ')

            srv.starttls()
            srv.login(email_id, passwd)
            df, cols = extract_file_data(fname)
            for address, body in format_text(msg, df, add_file, cols):
                if confirm:
                    click.echo(body)
                    if click.confirm('are you sure you want to proceed with this email?'):
                        confirm = False
                    else:
                        sys.eexit('Aborted!')
                srv.sendmail(from_addr=email_id, to_addrs=address, msg=create_mail(
                    msg=body, sender=email_id, target=address, sub=sub, attach=attach))
                sleep(1.0)
        else:
            with open(add_file, 'r') as afile:
                add_list = [add.strip() for add in afile.readlines()]
            for address in add_list:
                if confirm:
                    click.echo(msg)
                    if click.confirm('are you sure you want to proceed with this email?'):
                        confirm = False
                        click.clear()
                    else:
                        sys.exit('Aborted!')
                srv.sendmail(from_addr=email_id, to_addrs=address, msg=create_mail(
                    msg=msg, sender=email_id, target=address, sub=sub, attach=attach))

    finally:
        srv.quit()


def get_credentials() -> tuple:
    while True:
        email_id = click.prompt('enter your email id \n', prompt_suffix='>> ')
        passwd = keyring.get_password(service_id, email_id)
        if passwd:
            res = click.prompt(
                'type del to delete this email anything else to continue \n', prompt_suffix='>> ', default='', show_default=False)
            if res.lower() == 'del':
                keyring.delete_password(service_id, email_id)
                click.echo('deleted!')
                continue
            return email_id, passwd
        else:
            passwd = click.prompt(
                'new email? enter password \n', prompt_suffix='>> ')
            keyring.set_password(service_id, email_id, passwd)
            return email_id, passwd


def send_regular_mail(ctx, _, value):
    try:
        if not value:
            p = ctx.params
            if click.confirm('are you sure you want to send a regular email?'):
                email_id, passwd = get_credentials()
                write_mail(fname=None, add_file=p.get(
                    'target_file'), email_id=email_id, passwd=passwd, attach=p.get('attach'))
                ctx.exit('mailed succesfully!')
            else:
                ctx.exit('Aborted!')
    except smtplib.SMTPAuthenticationError:
        click.echo('Please check the username and password entered!')
        click.echo(
            '... or if you have 2 factor authentication turned on then you need to use an app password instead of your regular one.')
        keyring.delete_password(service_id, email_id)
        ctx.exit()
    except TypeError:
        click.echo('The file seems to be of the wrong type!')
        ctx.exit()


@click.command()
@click.argument('target_file', type=click.Path(exists=True))
@click.option('--attach', '-a', 'attach', type=click.Path(exists=True), help='path to attachment file')
@click.option('fname', '--fname', '-f', type=click.Path(exists=True), callback=send_regular_mail, help='path to the csv file')
def cli_face(target_file, fname, attach) -> None:
    ''' This script intends to automate mailing through gmail, just type the name of the script followed by the 
    file that contains the list of addresses, this file is supposed to be a plain text file containing a single 
    email address on each line. There is a also an option to add variables to your email body, just specify a csv
    file with all the data that you want to use and type $column_name in the body to substitute the value of the column. 
    attachments are supported as well.'''
    try:
        email_id, passwd = get_credentials()
        write_mail(fname=fname, add_file=target_file,
                   email_id=email_id, passwd=passwd, attach=attach)
        sys.exit('mailed succesfully!')
    except smtplib.SMTPAuthenticationError:
        click.echo('Please check the username and password entered!')
        click.echo(
            '... or if you have 2 factor authentication turned on then you need to use an app password instead of your regular one.')
        keyring.delete_password(service_id, email_id)
        sys.exit()
    except TypeError:
        click.echo(
            'one or both of the files seem to be the wrong type, please check them again!')
        sys.exit()


cli_face()
