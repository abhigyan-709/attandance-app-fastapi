from fastapi_mail import FastMail, MessageSchema
from models.email_config import conf

async def send_registration_email(email: str, username: str):
    subject = "Welcome to Project DevOps!"
    body = f"""
    <html>
        <body>
            <h2>Hi {username},</h2>
            <p>Welcome to Project DevOps! Your registration for Python & Cloud Computing Bootcamp is Successful.</p>
            <p>Please join our WhatApp Group for further communication.</p>
            <link>https://chat.whatsapp.com/EnjQWucvrFvDeTMQoNNSXd</link>
            <p>We are excited to have you with us.</p>
            <br>
            <p>Best regards,</p>
            <p>Your Company Team</p>
        </body>
    </html>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
