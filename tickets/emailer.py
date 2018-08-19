import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class Email:

    def __init__(self, from_account, password, to_account, subject, body):
        self.from_account = from_account
        self.password = password
        self.to_account = to_account
        self.subject = subject
        self.body = body
        self.msg = self.build_message()

    def build_message(self):
        msg = MIMEMultipart()
        msg['From'] = self.from_account
        msg['To'] = self.to_account
        msg['Subject'] = self.subject
        msg.attach(MIMEText(self.body, 'plain'))
        return msg

    def send(self):
        server = smtplib.SMTP(host='smtp.gmail.com', port=587)
        with server:
            try:
                server.starttls()
                server.login(self.msg['From'], self.password)
                server.sendmail(self.msg['From'], self.msg['To'], self.msg.as_string())
                print("Successfully sent email to {}".format(self.msg['To']))
            except SMTPAuthenticationError:
                print("Incorrect login information for {}".format(self.msg['From']))
            
