from fastapi_mail import FastMail, MessageSchema
from models.email_config import conf

async def send_registration_email(email: str, first_name: str, last_name: str):
    # Mail subject
    subject = "Congratulations! You are Registered for Project DevOps Training"

    # HTML Email Body
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #1A237E; text-align: center;">Dear {first_name} {last_name},</h2>
                <p>Congratulations! You have successfully registered for the <b>3-Months Free Certificate Training Program</b> in <b>Python, Cloud Computing & DevOps</b>, hosted by <b>Project DevOps</b> in collaboration with <b>Support Foundation</b>.</p>

                <h3 style="color: #FF5722;">Training Details:</h3>
                <ul>
                    <li><b>📅 Start From:</b> 24th February 2025</li>
                    <<li><b>⏰ Time:</b> 8:30 PM – 9:30 PM IST</li>
                    <li><b>🖥 Mode:</b> Online</li>
                    <li><b>📜 Duration:</b> 3 Months</li>
                    <li><b>💰 Cost:</b> Free</li>
                    <li><b>🎯 Certificate of Completion</b> will be provided upon successful completion of the training and assessments.</li>
                </ul>

                <p>This program covers Python programming, cloud computing, and DevOps methodologies with hands-on practice to enhance your skills. Placement assistance and boot camps for internships and job placements are available after training.</p>

                <h3 style="color: #388E3C;">Join the WhatsApp Group:</h3>
                <p>Click the link below to join our official WhatsApp group for further details and to get the session joining link:</p>
                <p><a href="https://chat.whatsapp.com/EKaQMLEXQ2nBr2HQlqwbQG" style="color: #0288D1; font-weight: bold;">Join WhatsApp Group</a></p>

                <h3>For any queries, feel free to contact us:</h3>
                <p><b>📧 Email:</b> connect@projectdevops.in / training@projectdevops.in</p>
                <p><b>📞 Phone:</b> +91 9135610801</p>
                <p><b>🌐 Website:</b> <a href="https://www.projectdevops.in" style="color: #0288D1;">www.projectdevops.in</a></p>

                <p style="text-align: center; font-weight: bold;">We are excited to have you on board and look forward to an enriching learning experience together!</p>

                <p style="text-align: center;"><b>Best regards,<br>Project DevOps Team</b></p>
            </div>
        </body>
    </html>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        cc=["projectdevops709@gmail.com"],  # Added CC
        body=body,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)

async def send_password_reset_email(email: str, reset_link: str):
    subject = "Password Reset Request for Project DevOps"

    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #1A237E; text-align: center;">Password Reset Request</h2>
                <p>Hello,</p>
                <p>We received a request to reset your password for your Project DevOps account. Click the button below to set a new password:</p>

                <p style="text-align: center;">
                    <a href="{reset_link}" style="display: inline-block; padding: 10px 20px; color: white; background-color: #FF5722; text-decoration: none; border-radius: 5px;">
                        Reset Password
                    </a>
                </p>

                <p>If you did not request a password reset, please ignore this email.</p>
                <p>This link will expire in 15 minutes.</p>

                <p>Best regards,<br><b>Project DevOps Team</b></p>
            </div>
        </body>
    </html>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        cc=["projectdevops709@gmail.com"],  # Added CC
        body=body,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)


async def send_username_recovery_email(email: str, username: str):
    subject = "Username Recovery for Project DevOps"

    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #1A237E; text-align: center;">Username Recovery Request</h2>
                <p>Hello,</p>
                <p>We received a request to recover your username for your Project DevOps account.</p>

                <p><b>Your Username:</b> <span style="color: #FF5722; font-size: 18px;">{username}</span></p>

                <p>If you did not request this, please ignore this email.</p>

                <p>Best regards,<br><b>Project DevOps Team</b></p>
            </div>
        </body>
    </html>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        cc=["projectdevops709@gmail.com"],  # Added CC
        body=body,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)