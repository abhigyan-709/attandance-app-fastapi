# from fastapi_mail import FastMail, MessageSchema
# from models.email_config import conf

# async def send_registration_email(email: str, username: str):
#     # mail to be sent
#     subject = "Welcome to Project DevOps!"
#     body = f"""
#     <html>
#         <body>
#             <h2>Hi {username},</h2>
#             <p>Welcome to Project DevOps! Your registration for Python & Cloud Computing Bootcamp is Successful.</p>
#             <p>Please join our WhatApp Group for further communication.</p>
#             <link>https://chat.whatsapp.com/EnjQWucvrFvDeTMQoNNSXd</link>
#             <p>We are excited to have you with us.</p>
#             <br>
#             <p>Best regards,</p>
#             <p>Your Company Team</p>
#         </body>
#     </html>
#     """

#     message = MessageSchema(
#         subject=subject,
#         recipients=[email],
#         body=body,
#         subtype="html"
#     )

#     fm = FastMail(conf)
#     await fm.send_message(message)

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
                    <li><b>📅 Start From:</b> 16th February 2025</li>
                    <li><b>⏰ Time:</b> 7:00 PM – 8:15 PM IST</li>
                    <li><b>🖥 Mode:</b> Online</li>
                    <li><b>📜 Duration:</b> 3 Months</li>
                    <li><b>💰 Cost:</b> Free</li>
                    <li><b>🎯 Certificate of Completion</b> will be provided upon successful completion of the training and assessments.</li>
                </ul>

                <p>This program covers Python programming, cloud computing, and DevOps methodologies with hands-on practice to enhance your skills. Placement assistance and boot camps for internships and job placements are available after training.</p>

                <h3 style="color: #388E3C;">Join the WhatsApp Group:</h3>
                <p>Click the link below to join our official WhatsApp group for further details and to get the session joining link:</p>
                <p><a href="https://chat.whatsapp.com/EnjQWucvrFvDeTMQoNNSXd" style="color: #0288D1; font-weight: bold;">Join WhatsApp Group</a></p>


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
        body=body,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
