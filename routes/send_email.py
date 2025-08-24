# from fastapi_mail import FastMail, MessageSchema
# from models.email_config import conf

# async def send_registration_email(email: str, first_name: str, last_name: str):
#     # Mail subject
#     subject = "Congratulations! You are Registered for Project DevOps Training"

#     # HTML Email Body
#     body = f"""
#     <html>
#         <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
#             <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
#                 <h2 style="color: #1A237E; text-align: center;">Dear {first_name} {last_name},</h2>
#                 <p>Congratulations! You have successfully registered for the <b>3-Months Free Certificate Training Program</b> in <b>Python, Cloud Computing & DevOps</b>, hosted by <b>Project DevOps</b> in collaboration with <b>Support Foundation</b>.</p>

#                 <h3 style="color: #FF5722;">Training Details:</h3>
#                 <ul>
#                     <li><b>📅 Start From:</b> 24th February 2025</li>
#                     <<li><b>⏰ Time:</b> 8:30 PM – 9:30 PM IST</li>
#                     <li><b>🖥 Mode:</b> Online</li>
#                     <li><b>📜 Duration:</b> 3 Months</li>
#                     <li><b>💰 Cost:</b> Free</li>
#                     <li><b>🎯 Certificate of Completion</b> will be provided upon successful completion of the training and assessments.</li>
#                 </ul>

#                 <p>This program covers Python programming, cloud computing, and DevOps methodologies with hands-on practice to enhance your skills. Placement assistance and boot camps for internships and job placements are available after training.</p>

#                 <h3 style="color: #388E3C;">Join the WhatsApp Group:</h3>
#                 <p>Click the link below to join our official WhatsApp group for further details and to get the session joining link:</p>
#                 <p><a href="https://chat.whatsapp.com/EpnKFXIdJdPI2e8w7IO61H" style="color: #0288D1; font-weight: bold;">Join WhatsApp Group</a></p>

#                 <h3>For any queries, feel free to contact us:</h3>
#                 <p><b>📧 Email:</b> connect@projectdevops.in / training@projectdevops.in</p>
#                 <p><b>📞 Phone:</b> +91 9135610801</p>
#                 <p><b>🌐 Website:</b> <a href="https://www.projectdevops.in" style="color: #0288D1;">www.projectdevops.in</a></p>

#                 <p style="text-align: center; font-weight: bold;">We are excited to have you on board and look forward to an enriching learning experience together!</p>

#                 <p style="text-align: center;"><b>Best regards,<br>Project DevOps Team</b></p>
#             </div>
#         </body>
#     </html>
#     """

#     message = MessageSchema(
#         subject=subject,
#         recipients=[email],
#         cc=["projectdevops709@gmail.com"],  # Added CC
#         body=body,
#         subtype="html"
#     )

#     fm = FastMail(conf)
#     await fm.send_message(message)

# async def send_password_reset_email(email: str, reset_link: str):
#     subject = "Password Reset Request for Project DevOps"

#     body = f"""
#     <html>
#         <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
#             <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
#                 <h2 style="color: #1A237E; text-align: center;">Password Reset Request</h2>
#                 <p>Hello,</p>
#                 <p>We received a request to reset your password for your Project DevOps account. Click the button below to set a new password:</p>

#                 <p style="text-align: center;">
#                     <a href="{reset_link}" style="display: inline-block; padding: 10px 20px; color: white; background-color: #FF5722; text-decoration: none; border-radius: 5px;">
#                         Reset Password
#                     </a>
#                 </p>

#                 <p>If you did not request a password reset, please ignore this email.</p>
#                 <p>This link will expire in 15 minutes.</p>

#                 <p>Best regards,<br><b>Project DevOps Team</b></p>
#             </div>
#         </body>
#     </html>
#     """

#     message = MessageSchema(
#         subject=subject,
#         recipients=[email],
#         cc=["projectdevops709@gmail.com"],  # Added CC
#         body=body,
#         subtype="html"
#     )

#     fm = FastMail(conf)
#     await fm.send_message(message)


# async def send_username_recovery_email(email: str, username: str):
#     subject = "Username Recovery for Project DevOps"

#     # Wrap username in double quotes
#     formatted_username = f'"{username}"'

#     body = f"""
#     <html>
#         <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
#             <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
#                 <h2 style="color: #1A237E; text-align: center;">Username Recovery Request</h2>
#                 <p>Hello,</p>
#                 <p>We received a request to recover your username for your Project DevOps account.</p>

#                 <p><b>Your Username:</b> <span style="color: #FF5722; font-size: 18px;">{formatted_username}</span></p>

#                 <p>If you did not request this, please ignore this email.</p>

#                 <p>Best regards,<br><b>Project DevOps Team</b></p>
#             </div>
#         </body>
#     </html>
#     """

#     message = MessageSchema(
#         subject=subject,
#         recipients=[email],
#         cc=["projectdevops709@gmail.com"],  # Keep CC
#         body=body,
#         subtype="html"
#     )

#     fm = FastMail(conf)
#     await fm.send_message(message)


from fastapi_mail import FastMail, MessageSchema
from models.email_config import conf

async def send_registration_email(email: str, first_name: str, last_name: str):
    # Subject line for user account registration
    subject = "Welcome to VoloBlink – Your Account is Ready!"

    body = f"""
    <html>
      <body style="margin:0;padding:0;background:#FFF8E1;font-family:Arial,sans-serif;color:#2f2f2f;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#FFF8E1;padding:24px 0;">
          <tr>
            <td align="center">
              <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#ffffff;border:1px solid #e9e9e9;border-radius:12px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,0.06);">
                
                <!-- Header -->
                <tr>
                  <td style="background:#00695C;padding:20px 24px;text-align:center;">
                    <div style="font-size:22px;line-height:1.2;color:#ffffff;font-weight:bold;">
                      VoloBlink
                    </div>
                    <div style="font-size:12px;color:#D0F2EB;opacity:.9;margin-top:4px;">
                      Vocal for Local
                    </div>
                  </td>
                </tr>

                <!-- Greeting -->
                <tr>
                  <td style="padding:24px 24px 8px 24px;">
                    <h2 style="margin:0 0 8px 0;color:#1A237E;font-size:20px;">
                      Dear {first_name} {last_name},
                    </h2>
                    <p style="margin:0;color:#424242;font-size:14px;line-height:1.7;">
                      Congratulations! 🎉 Your account has been successfully registered in the 
                      <b>VoloBlink (Vocal for Local)</b> app.
                    </p>
                  </td>
                </tr>

                <!-- Info -->
                <tr>
                  <td style="padding:16px 24px 0 24px;">
                    <p style="margin:0;color:#424242;font-size:14px;line-height:1.7;">
                      You can now log in to the application using your 
                      <b>username</b> and <b>password</b>.
                    </p>
                    <p style="margin:12px 0 0 0;color:#424242;font-size:14px;line-height:1.7;">
                      Explore authentic local products, connect with vendors, and enjoy the 
                      <b>Vocal for Local</b> experience with VoloBlink.
                    </p>
                  </td>
                </tr>

                <!-- Next Steps -->
                <tr>
                  <td style="padding:20px 24px;text-align:center;">
                    <a href="https://www.projectdevops.in" 
                       style="display:inline-block;background:#FF6F61;color:#ffffff;text-decoration:none;
                              padding:12px 20px;border-radius:8px;font-weight:bold;">
                      Login to VoloBlink
                    </a>
                  </td>
                </tr>

                <!-- Contacts -->
                <tr>
                  <td style="padding:24px;">
                    <div style="border-top:1px solid #eeeeee;margin:0 0 16px 0;"></div>
                    <h3 style="margin:0 0 8px 0;color:#1A237E;font-size:16px;">Need help?</h3>
                    <p style="margin:0;color:#424242;font-size:14px;line-height:1.8;">
                      <b>📧 Email:</b> connect@projectdevops.in<br/>
                      <b>📞 Phone:</b> +91 9135610801<br/>
                      <b>🌐 Website:</b> <a href="https://www.projectdevops.in" style="color:#00695C;text-decoration:none;">www.projectdevops.in</a>
                    </p>
                  </td>
                </tr>

                <!-- Footer -->
                <tr>
                  <td style="background:#F8FFFC;padding:16px 24px;text-align:center;border-top:1px solid #e9f3f0;">
                    <p style="margin:0;color:#2e7d73;font-weight:bold;">
                      Welcome to the VoloBlink family!
                    </p>
                    <p style="margin:4px 0 0 0;color:#00695C;font-weight:bold;">— The VoloBlink Team</p>
                  </td>
                </tr>
              </table>

              <!-- tiny footer -->
              <div style="max-width:600px;color:#888888;font-size:11px;margin:12px auto 0 auto;text-align:center;">
                You received this email because you registered for a VoloBlink account. 
                If this wasn’t you, please ignore this email.
              </div>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[email],
        cc=["projectdevops709@gmail.com"],  # unchanged
        body=body,
        subtype="html",
    )

    fm = FastMail(conf)
    await fm.send_message(message)
