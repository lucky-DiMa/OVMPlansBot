import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mytime import beauty_date, next_send_day


def send_table(receiver_email: str):
    subject = f"Планы на {beauty_date(next_send_day())}"
    body = subject
    sender_email = "plansbot@ovm.group"
    password = '(M)foI41'
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message["Bcc"] = receiver_email

    message.attach(MIMEText(body, "plain"))

    filename = "plans.xlsx"
    with open(filename, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    encoders.encode_base64(part)

    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {filename}",
    )

    message.attach(part)
    text = message.as_string()

    # context = ssl.create_default_context()
    server = smtplib.SMTP('mail.ovm.su', 587)
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, text)
    server.quit()
