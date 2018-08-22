import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from O365 import Message

class O365Email:

    def __init__(self, email_auth, to_account, subject, body):
        self.auth = email_auth
        self.to_account = to_account
        self.subject = subject
        self.body = body
        self.msg = self.build_message()

    def build_message(self):
        m = Message(auth=self.auth)
        m.setRecipients(self.to_account)
        m.setSubject(self.subject)
        m.setBodyHTML(self.body)
        return m

    def send(self):
        if self.msg.sendMessage():
            print ("Succesfully sent email to {}".format(self.msg.json['ToRecipients'][0]['EmailAddress']['Address']))
        else:
            print("Failed to send email to {}".format(self.msg.json['ToRecipients'][0]['EmailAddress']['Address']))

class SmtpAuth:

    def __init__(self, host, port, from_account, password):
        self.host = host
        self.port = port
        self.from_account = from_account
        self.password = password

class SmtpEmail:
    def __init__(self, email_auth, to_account, subject, body):
        self.auth = email_auth
        self.to_account = to_account
        self.subject = subject
        self.body = body
        self.msg = self.build_message()

    def build_message(self):
        msg = MIMEMultipart()
        msg['From'] = self.auth.from_account
        msg['To'] = self.to_account
        msg['Subject'] = self.subject
        msg.attach(MIMEText(self.body, 'plain'))
        return msg

    def send(self):
        server = smtplib.SMTP(host=self.auth.host, port=self.auth.port)
        with server:
            try:
                server.starttls()
                server.login(self.msg['From'], self.auth.password)
                server.sendmail(self.msg['From'], self.msg['To'], self.msg.as_string())
                print("Successfully sent email to {}".format(self.msg['To']))
            except SMTPAuthenticationError:
                print("Incorrect login information for {}".format(self.msg['From']))
