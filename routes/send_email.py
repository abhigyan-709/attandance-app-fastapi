# # from fastapi_mail import FastMail, MessageSchema
# # from models.email_config import conf

# # async def send_registration_email(email: str, first_name: str, last_name: str):
# #     # Mail subject
# #     subject = "Congratulations! You are Registered for Project DevOps Training"

# #     # HTML Email Body
# #     body = f"""
# #     <html>
# #         <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
# #             <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
# #                 <h2 style="color: #1A237E; text-align: center;">Dear {first_name} {last_name},</h2>
# #                 <p>Congratulations! You have successfully registered for the <b>3-Months Free Certificate Training Program</b> in <b>Python, Cloud Computing & DevOps</b>, hosted by <b>Project DevOps</b> in collaboration with <b>Support Foundation</b>.</p>

# #                 <h3 style="color: #FF5722;">Training Details:</h3>
# #                 <ul>
# #                     <li><b>📅 Start From:</b> 24th February 2025</li>
# #                     <<li><b>⏰ Time:</b> 8:30 PM – 9:30 PM IST</li>
# #                     <li><b>🖥 Mode:</b> Online</li>
# #                     <li><b>📜 Duration:</b> 3 Months</li>
# #                     <li><b>💰 Cost:</b> Free</li>
# #                     <li><b>🎯 Certificate of Completion</b> will be provided upon successful completion of the training and assessments.</li>
# #                 </ul>

# #                 <p>This program covers Python programming, cloud computing, and DevOps methodologies with hands-on practice to enhance your skills. Placement assistance and boot camps for internships and job placements are available after training.</p>

# #                 <h3 style="color: #388E3C;">Join the WhatsApp Group:</h3>
# #                 <p>Click the link below to join our official WhatsApp group for further details and to get the session joining link:</p>
# #                 <p><a href="https://chat.whatsapp.com/EpnKFXIdJdPI2e8w7IO61H" style="color: #0288D1; font-weight: bold;">Join WhatsApp Group</a></p>

# #                 <h3>For any queries, feel free to contact us:</h3>
# #                 <p><b>📧 Email:</b> connect@projectdevops.in / training@projectdevops.in</p>
# #                 <p><b>📞 Phone:</b> +91 9135610801</p>
# #                 <p><b>🌐 Website:</b> <a href="https://www.projectdevops.in" style="color: #0288D1;">www.projectdevops.in</a></p>

# #                 <p style="text-align: center; font-weight: bold;">We are excited to have you on board and look forward to an enriching learning experience together!</p>

# #                 <p style="text-align: center;"><b>Best regards,<br>Project DevOps Team</b></p>
# #             </div>
# #         </body>
# #     </html>
# #     """

# #     message = MessageSchema(
# #         subject=subject,
# #         recipients=[email],
# #         cc=["projectdevops709@gmail.com"],  # Added CC
# #         body=body,
# #         subtype="html"
# #     )

# #     fm = FastMail(conf)
# #     await fm.send_message(message)

# # async def send_password_reset_email(email: str, reset_link: str):
# #     subject = "Password Reset Request for Project DevOps"

# #     body = f"""
# #     <html>
# #         <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
# #             <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
# #                 <h2 style="color: #1A237E; text-align: center;">Password Reset Request</h2>
# #                 <p>Hello,</p>
# #                 <p>We received a request to reset your password for your Project DevOps account. Click the button below to set a new password:</p>

# #                 <p style="text-align: center;">
# #                     <a href="{reset_link}" style="display: inline-block; padding: 10px 20px; color: white; background-color: #FF5722; text-decoration: none; border-radius: 5px;">
# #                         Reset Password
# #                     </a>
# #                 </p>

# #                 <p>If you did not request a password reset, please ignore this email.</p>
# #                 <p>This link will expire in 15 minutes.</p>

# #                 <p>Best regards,<br><b>Project DevOps Team</b></p>
# #             </div>
# #         </body>
# #     </html>
# #     """

# #     message = MessageSchema(
# #         subject=subject,
# #         recipients=[email],
# #         cc=["projectdevops709@gmail.com"],  # Added CC
# #         body=body,
# #         subtype="html"
# #     )

# #     fm = FastMail(conf)
# #     await fm.send_message(message)


# # async def send_username_recovery_email(email: str, username: str):
# #     subject = "Username Recovery for Project DevOps"

# #     # Wrap username in double quotes
# #     formatted_username = f'"{username}"'

# #     body = f"""
# #     <html>
# #         <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
# #             <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
# #                 <h2 style="color: #1A237E; text-align: center;">Username Recovery Request</h2>
# #                 <p>Hello,</p>
# #                 <p>We received a request to recover your username for your Project DevOps account.</p>

# #                 <p><b>Your Username:</b> <span style="color: #FF5722; font-size: 18px;">{formatted_username}</span></p>

# #                 <p>If you did not request this, please ignore this email.</p>

# #                 <p>Best regards,<br><b>Project DevOps Team</b></p>
# #             </div>
# #         </body>
# #     </html>
# #     """

# #     message = MessageSchema(
# #         subject=subject,
# #         recipients=[email],
# #         cc=["projectdevops709@gmail.com"],  # Keep CC
# #         body=body,
# #         subtype="html"
# #     )

# #     fm = FastMail(conf)
# #     await fm.send_message(message)

# from fastapi_mail import FastMail, MessageSchema
# from models.email_config import conf

# # -------------------------
# # Registration (VoloBlink)
# # -------------------------
# async def send_registration_email(email: str, first_name: str, last_name: str):
#     subject = "Welcome to VoloBlink – Your Account is Ready!"

#     body = f"""
#     <html>
#       <body style="margin:0;padding:0;background:#FFF8E1;font-family:Arial,sans-serif;color:#2f2f2f;">
#         <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#FFF8E1;padding:24px 0;">
#           <tr>
#             <td align="center">
#               <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#ffffff;border:1px solid #e9e9e9;border-radius:12px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,0.06);">
                
#                 <!-- Header -->
#                 <tr>
#                   <td style="background:#00695C;padding:20px 24px;text-align:center;">
#                     <div style="font-size:22px;line-height:1.2;color:#ffffff;font-weight:bold;">
#                       VoloBlink
#                     </div>
#                     <div style="font-size:12px;color:#D0F2EB;opacity:.9;margin-top:4px;">
#                       Vocal for Local
#                     </div>
#                   </td>
#                 </tr>

#                 <!-- Greeting -->
#                 <tr>
#                   <td style="padding:24px 24px 8px 24px;">
#                     <h2 style="margin:0 0 8px 0;color:#1A237E;font-size:20px;">
#                       Dear {first_name} {last_name},
#                     </h2>
#                     <p style="margin:0;color:#424242;font-size:14px;line-height:1.7;">
#                       Congratulations! 🎉 Your account has been successfully registered in the 
#                       <b>VoloBlink (Vocal for Local)</b> app.
#                     </p>
#                   </td>
#                 </tr>

#                 <!-- Info -->
#                 <tr>
#                   <td style="padding:16px 24px 0 24px;">
#                     <p style="margin:0;color:#424242;font-size:14px;line-height:1.7;">
#                       You can now log in to the application using your 
#                       <b>username</b> and <b>password</b>.
#                     </p>
#                     <p style="margin:12px 0 0 0;color:#424242;font-size:14px;line-height:1.7;">
#                       Explore authentic local products, connect with vendors, and enjoy the 
#                       <b>Vocal for Local</b> experience with VoloBlink.
#                     </p>
#                   </td>
#                 </tr>

#                 <!-- Next Steps -->
#                 <tr>
#                   <td style="padding:20px 24px;text-align:center;">
#                     <a href="https://www.projectdevops.in" 
#                        style="display:inline-block;background:#FF6F61;color:#ffffff;text-decoration:none;
#                               padding:12px 20px;border-radius:8px;font-weight:bold;">
#                       Login to VoloBlink
#                     </a>
#                   </td>
#                 </tr>

#                 <!-- Contacts -->
#                 <tr>
#                   <td style="padding:24px;">
#                     <div style="border-top:1px solid #eeeeee;margin:0 0 16px 0;"></div>
#                     <h3 style="margin:0 0 8px 0;color:#1A237E;font-size:16px;">Need help?</h3>
#                     <p style="margin:0;color:#424242;font-size:14px;line-height:1.8;">
#                       <b>📧 Email:</b> connect@projectdevops.in<br/>
#                       <b>📞 Phone:</b> +91 9135610801<br/>
#                       <b>🌐 Website:</b> <a href="https://www.projectdevops.in" style="color:#00695C;text-decoration:none;">www.projectdevops.in</a>
#                     </p>
#                   </td>
#                 </tr>

#                 <!-- Footer -->
#                 <tr>
#                   <td style="background:#F8FFFC;padding:16px 24px;text-align:center;border-top:1px solid #e9f3f0;">
#                     <p style="margin:0;color:#2e7d73;font-weight:bold;">
#                       Welcome to the VoloBlink family!
#                     </p>
#                     <p style="margin:4px 0 0 0;color:#00695C;font-weight:bold;">— The VoloBlink Team</p>
#                   </td>
#                 </tr>
#               </table>

#               <div style="max-width:600px;color:#888888;font-size:11px;margin:12px auto 0 auto;text-align:center;">
#                 You received this email because you registered for a VoloBlink account. 
#                 If this wasn’t you, please ignore this email.
#               </div>
#             </td>
#           </tr>
#         </table>
#       </body>
#     </html>
#     """

#     message = MessageSchema(
#         subject=subject,
#         recipients=[email],
#         cc=["projectdevops709@gmail.com"],
#         body=body,
#         subtype="html",
#     )

#     fm = FastMail(conf)
#     await fm.send_message(message)

# # -------------------------
# # Password Reset (unchanged)
# # -------------------------
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
#         cc=["projectdevops709@gmail.com"],
#         body=body,
#         subtype="html"
#     )

#     fm = FastMail(conf)
#     await fm.send_message(message)

# # --------------------------------
# # Username Recovery (unchanged)
# # --------------------------------
# async def send_username_recovery_email(email: str, username: str):
#     subject = "Username Recovery for Project DevOps"

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
#         cc=["projectdevops709@gmail.com"],
#         body=body,
#         subtype="html"
#     )

#     fm = FastMail(conf)
#     await fm.send_message(message)

# services/email.py
from typing import Dict, Any
from fastapi_mail import FastMail, MessageSchema
from models.email_config import conf
from datetime import datetime

# CC admins for every transactional mail where needed
ADMIN_CC = ["projectdevops709@gmail.com", "sup.fou.958@gmail.com"]


# -------------------------
# Registration (VoloBlink)
# -------------------------
# async def send_registration_email(email: str, first_name: str, last_name: str):
#     subject = "Welcome to VoloBlink – Your Account is Ready!"

#     body = f"""
#     <html>
#       <body style="margin:0;padding:0;background:#FFF8E1;font-family:Arial,sans-serif;color:#2f2f2f;">
#         <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#FFF8E1;padding:24px 0;">
#           <tr>
#             <td align="center">
#               <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#ffffff;border:1px solid #e9e9e9;border-radius:12px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,0.06);">
#                 <tr>
#                   <td style="background:#00695C;padding:20px 24px;text-align:center;">
#                     <div style="font-size:22px;line-height:1.2;color:#ffffff;font-weight:bold;">VoloBlink</div>
#                     <div style="font-size:12px;color:#D0F2EB;opacity:.9;margin-top:4px;">Vocal for Local</div>
#                   </td>
#                 </tr>
#                 <tr>
#                   <td style="padding:24px 24px 8px 24px;">
#                     <h2 style="margin:0 0 8px 0;color:#1A237E;font-size:20px;">Dear {first_name} {last_name},</h2>
#                     <p style="margin:0;color:#424242;font-size:14px;line-height:1.7;">
#                       Congratulations! 🎉 Your account has been successfully registered in the
#                       <b>VoloBlink (Vocal for Local)</b> app.
#                     </p>
#                   </td>
#                 </tr>
#                 <tr>
#                   <td style="padding:16px 24px 0 24px;">
#                     <p style="margin:0;color:#424242;font-size:14px;line-height:1.7;">
#                       You can now log in to the application using your <b>username</b> and <b>password</b>.
#                     </p>
#                     <p style="margin:12px 0 0 0;color:#424242;font-size:14px;line-height:1.7;">
#                       Explore authentic local products, connect with vendors, and enjoy the <b>Vocal for Local</b> experience with VoloBlink.
#                     </p>
#                   </td>
#                 </tr>
#                 <tr>
#                   <td style="padding:20px 24px;text-align:center;">
#                     <a href="https://www.projectdevops.in"
#                        style="display:inline-block;background:#FF6F61;color:#ffffff;text-decoration:none;
#                               padding:12px 20px;border-radius:8px;font-weight:bold;">
#                       Login to VoloBlink
#                     </a>
#                   </td>
#                 </tr>
#                 <tr>
#                   <td style="padding:24px;">
#                     <div style="border-top:1px solid #eeeeee;margin:0 0 16px 0;"></div>
#                     <h3 style="margin:0 0 8px 0;color:#1A237E;font-size:16px;">Need help?</h3>
#                     <p style="margin:0;color:#424242;font-size:14px;line-height:1.8;">
#                       <b>📧 Email:</b> connect@projectdevops.in<br/>
#                       <b>📞 Phone:</b> +91 9135610801<br/>
#                       <b>🌐 Website:</b> <a href="https://www.projectdevops.in" style="color:#00695C;text-decoration:none;">www.projectdevops.in</a>
#                     </p>
#                   </td>
#                 </tr>
#                 <tr>
#                   <td style="background:#F8FFFC;padding:16px 24px;text-align:center;border-top:1px solid #e9f3f0;">
#                     <p style="margin:0;color:#2e7d73;font-weight:bold;">Welcome to the VoloBlink family!</p>
#                     <p style="margin:4px 0 0 0;color:#00695C;font-weight:bold;">— The VoloBlink Team</p>
#                   </td>
#                 </tr>
#               </table>
#               <div style="max-width:600px;color:#888888;font-size:11px;margin:12px auto 0 auto;text-align:center;">
#                 You received this email because you registered for a VoloBlink account. If this wasn’t you, please ignore this email.
#               </div>
#             </td>
#           </tr>
#         </table>
#       </body>
#     </html>
#     """

#     message = MessageSchema(
#         subject=subject,
#         recipients=[email],
#         cc=["projectdevops709@gmail.com"],  # keep your original CC for registration
#         body=body,
#         subtype="html",
#     )
#     fm = FastMail(conf)
#     await fm.send_message(message)

async def send_registration_email(email: str, first_name: str, last_name: str):
    subject = "Welcome to Gobarsahi Times – Your Account is Ready!"

    body = f"""
    <html>
      <body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;color:#e2e8f0;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#0f172a;padding:24px 0;">
          <tr>
            <td align="center">
              <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background:#1e293b;border:1px solid #334155;border-radius:12px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,0.3);">
                <tr>
                  <td style="background:linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);padding:20px 24px;text-align:center;">
                    <div style="font-size:24px;line-height:1.2;color:#ffffff;font-weight:bold;">📰 Gobarsahi Times</div>
                    <div style="font-size:12px;color:#bfdbfe;opacity:.95;margin-top:4px;">Muzaffarpur's Premier News Source</div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:24px 24px 8px 24px;">
                    <h2 style="margin:0 0 8px 0;color:#60a5fa;font-size:20px;">Dear {first_name} {last_name},</h2>
                    <p style="margin:0;color:#cbd5e1;font-size:14px;line-height:1.7;">
                      Congratulations! 🎉 Your account has been successfully registered with
                      <b style="color:#60a5fa;">Gobarsahi Times</b>.
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:16px 24px 0 24px;">
                    <p style="margin:0;color:#cbd5e1;font-size:14px;line-height:1.7;">
                      You can now log in to access your personalized news experience using your <b style="color:#60a5fa;">username</b> and <b style="color:#60a5fa;">password</b>.
                    </p>
                    <p style="margin:12px 0 0 0;color:#cbd5e1;font-size:14px;line-height:1.7;">
                      Stay updated with the latest news from <b style="color:#60a5fa;">Bihar, Muzaffarpur</b>, and surrounding areas. Get breaking news alerts and personalized content delivered right to you.
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 24px;text-align:center;">
                    <a href="https://gtnews18.in/login"
                       style="display:inline-block;background:linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);color:#ffffff;text-decoration:none;
                              padding:12px 24px;border-radius:24px;font-weight:bold;box-shadow:0 4px 12px rgba(29,78,216,0.4);">
                      Login to Gobarsahi Times
                    </a>
                  </td>
                </tr>
                <tr>
                  <td style="padding:24px;">
                    <div style="border-top:1px solid #334155;margin:0 0 16px 0;"></div>
                    <h3 style="margin:0 0 8px 0;color:#60a5fa;font-size:16px;">Need help?</h3>
                    <p style="margin:0;color:#cbd5e1;font-size:14px;line-height:1.8;">
                      <b style="color:#60a5fa;">📧 Email:</b> connect@projectdevops.in<br/>
                      <b style="color:#60a5fa;">📞 Phone:</b> +91 9135610801<br/>
                      <b style="color:#60a5fa;">🌐 Website:</b> <a href="https://gtnews18.in" style="color:#60a5fa;text-decoration:none;">gtnews18.in</a>
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="background:#1e3a8a;padding:16px 24px;text-align:center;border-top:1px solid #334155;">
                    <p style="margin:0;color:#bfdbfe;font-weight:bold;">Welcome to the Gobarsahi Times family!</p>
                    <p style="margin:4px 0 0 0;color:#60a5fa;font-weight:bold;">— The Gobarsahi Times Team</p>
                  </td>
                </tr>
              </table>
              <div style="max-width:600px;color:#64748b;font-size:11px;margin:12px auto 0 auto;text-align:center;">
                You received this email because you registered for a Gobarsahi Times account. If this wasn't you, please ignore this email.
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
        cc=["projectdevops709@gmail.com"],  # keep your original CC for registration
        body=body,
        subtype="html",
    )
    fm = FastMail(conf)
    await fm.send_message(message)


# -------------------------
# Password Reset
# -------------------------
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
            <a href="{reset_link}" style="display: inline-block; padding: 10px 20px; color: white; background-color: #FF5722; text-decoration: none; border-radius: 5px;">Reset Password</a>
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
        cc=["projectdevops709@gmail.com"],
        body=body,
        subtype="html"
    )
    fm = FastMail(conf)
    await fm.send_message(message)


# -------------------------
# Username Recovery
# -------------------------
async def send_username_recovery_email(email: str, username: str):
    subject = "Username Recovery for Project DevOps"
    formatted_username = f'"{username}"'
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
          <h2 style="color: #1A237E; text-align: center;">Username Recovery Request</h2>
          <p>Hello,</p>
          <p>We received a request to recover your username for your Project DevOps account.</p>
          <p><b>Your Username:</b> <span style="color: #FF5722; font-size: 18px;">{formatted_username}</span></p>
          <p>If you did not request this, please ignore this email.</p>
          <p>Best regards,<br><b>Project DevOps Team</b></p>
        </div>
      </body>
    </html>
    """
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        cc=["projectdevops709@gmail.com"],
        body=body,
        subtype="html"
    )
    fm = FastMail(conf)
    await fm.send_message(message)


# -------------------------
# NEW: Order Confirmation
# -------------------------
def _fmt_inr(v: float) -> str:
    return f"₹{v:,.2f}"

def _fmt_dt(iso_str: str) -> str:
    try:
        # tolerate "...Z"
        if iso_str and isinstance(iso_str, str):
            iso_str = iso_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        pass
    return iso_str or "-"

async def send_order_confirmation_email(order: Dict[str, Any]) -> None:
    """
    order: serialized order dict as returned to client (strings/ids already converted).
    Sends to user's email, CC admins (including sup.fou.958@gmail.com).
    """
    user = order.get("user") or {}
    email_to = user.get("email") or ""

    items = order.get("items") or []
    vendor = order.get("vendor") or {}
    payment = order.get("payment") or {}
    breakdown = payment.get("breakdown") or {}
    delivery_address = order.get("delivery_address") or "-"
    contact_phone = order.get("contact_phone") or "-"
    order_id = order.get("id") or order.get("_id") or "-"
    status = (order.get("status") or "").title() or "-"
    created_at = _fmt_dt(order.get("created_at") or "")

    # Build line items rows
    rows_html = ""
    for it in items:
        name = it.get("name") or "-"
        qty = int(it.get("quantity") or 0)
        unit_price = float(it.get("unit_price") or 0.0)
        subtotal = float(it.get("subtotal") or (qty * unit_price))
        gst_percent = float(it.get("gst_percent") or 0.0)
        gst_amount = float(it.get("gst_amount") or (subtotal * gst_percent / 100.0))
        line_total = subtotal + gst_amount
        rows_html += f"""
          <tr>
            <td style="padding:10px;border-bottom:1px solid #eee;">{name}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;text-align:center;">{qty}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;text-align:right;">{_fmt_inr(unit_price)}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;text-align:right;">{_fmt_inr(subtotal)}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;text-align:center;">{gst_percent:.0f}%</td>
            <td style="padding:10px;border-bottom:1px solid #eee;text-align:right;">{_fmt_inr(gst_amount)}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;text-align:right;font-weight:700;">{_fmt_inr(line_total)}</td>
          </tr>
        """

    product_total   = float(breakdown.get("product_total") or 0.0)
    gst_total       = float(breakdown.get("gst_total") or 0.0)
    delivery_charge = float(breakdown.get("delivery_charge") or 0.0)
    handling_fee    = float(breakdown.get("handling_fee") or 0.0)
    discount_amount = float(breakdown.get("discount_amount") or 0.0)
    final_amount    = float(breakdown.get("final_amount") or (product_total + gst_total + delivery_charge + handling_fee - discount_amount))

    pay_method = (payment.get("payment_method") or "-").upper()
    pay_status = (payment.get("status") or "-").title()

    subject = f"VoloBlink • Order Confirmation #{order_id}"

    body = f"""
    <html>
      <body style="margin:0;padding:0;background:#FFF8E1;font-family:Arial,sans-serif;color:#2f2f2f;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#FFF8E1;padding:24px 0;">
          <tr>
            <td align="center">
              <table role="presentation" width="760" cellspacing="0" cellpadding="0" style="background:#ffffff;border:1px solid #e9e9e9;border-radius:12px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,0.06);">
                <tr>
                  <td style="background:#00695C;padding:20px 24px;text-align:center;">
                    <div style="font-size:22px;line-height:1.2;color:#ffffff;font-weight:bold;">VoloBlink</div>
                    <div style="font-size:12px;color:#D0F2EB;opacity:.9;margin-top:4px;">Vocal for Local</div>
                  </td>
                </tr>

                <tr>
                  <td style="padding:18px 24px;">
                    <h2 style="margin:0 0 6px 0;color:#1A237E;font-size:20px;">Thank you for your order! 🎉</h2>
                    <p style="margin:6px 0 0 0;font-size:14px;color:#424242;">Your order has been received and is now being processed.</p>
                  </td>
                </tr>

                <!-- Order Summary -->
                <tr>
                  <td style="padding:0 24px 12px 24px;">
                    <table width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #eef2f1;border-radius:8px;">
                      <tr>
                        <td style="padding:12px 16px;border-bottom:1px solid #eef2f1;"><b>Order #</b>: {order_id}</td>
                        <td style="padding:12px 16px;border-bottom:1px solid #eef2f1;"><b>Placed</b>: {created_at}</td>
                        <td style="padding:12px 16px;border-bottom:1px solid #eef2f1;"><b>Status</b>: {status}</td>
                      </tr>
                      <tr>
                        <td style="padding:12px 16px;"><b>Payment</b>: {pay_method}</td>
                        <td style="padding:12px 16px;"><b>Payment Status</b>: {pay_status}</td>
                        <td style="padding:12px 16px;"><b>Total</b>: {_fmt_inr(final_amount)}</td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- Items Table -->
                <tr>
                  <td style="padding:0 24px 8px 24px;">
                    <h3 style="margin:8px 0 8px 0;color:#1A237E;font-size:16px;">Items</h3>
                    <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:13px;">
                      <thead>
                        <tr style="background:#F6FBF9;">
                          <th style="padding:10px;text-align:left;border-bottom:1px solid #ddd;">Item</th>
                          <th style="padding:10px;text-align:center;border-bottom:1px solid #ddd;">Qty</th>
                          <th style="padding:10px;text-align:right;border-bottom:1px solid #ddd;">Unit Price</th>
                          <th style="padding:10px;text-align:right;border-bottom:1px solid #ddd;">Subtotal</th>
                          <th style="padding:10px;text-align:center;border-bottom:1px solid #ddd;">GST</th>
                          <th style="padding:10px;text-align:right;border-bottom:1px solid #ddd;">GST Amt</th>
                          <th style="padding:10px;text-align:right;border-bottom:1px solid #ddd;">Line Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows_html}
                      </tbody>
                    </table>
                  </td>
                </tr>

                <!-- Totals -->
                <tr>
                  <td style="padding:8px 24px 16px 24px;">
                    <table width="100%" cellspacing="0" cellpadding="0" style="font-size:14px;">
                      <tr>
                        <td style="padding:6px 0;">Products</td>
                        <td style="padding:6px 0;text-align:right;">{_fmt_inr(product_total)}</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;">GST</td>
                        <td style="padding:6px 0;text-align:right;">{_fmt_inr(gst_total)}</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;">Delivery</td>
                        <td style="padding:6px 0;text-align:right;">{_fmt_inr(delivery_charge)}</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;">Handling</td>
                        <td style="padding:6px 0;text-align:right;">{_fmt_inr(handling_fee)}</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;">Discount</td>
                        <td style="padding:6px 0;text-align:right;">-{_fmt_inr(discount_amount)}</td>
                      </tr>
                      <tr>
                        <td colspan="2"><div style="border-top:1px dashed #e1e1e1;margin:6px 0;"></div></td>
                      </tr>
                      <tr>
                        <td style="padding:6px 0;font-weight:800;">Amount Payable</td>
                        <td style="padding:6px 0;text-align:right;font-weight:800;color:#FF6F61;">{_fmt_inr(final_amount)}</td>
                      </tr>
                    </table>
                    {"<div style='margin-top:8px;font-size:12px;color:#616161;'>Cash on Delivery selected. Please keep exact change if possible.</div>" if pay_method == "COD" else ""}
                  </td>
                </tr>

                <!-- Addresses -->
                <tr>
                  <td style="padding:8px 24px 18px 24px;">
                    <table width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #eef2f1;border-radius:8px;">
                      <tr style="background:#F6FBF9;">
                        <td style="padding:10px 14px;font-weight:bold;">Delivery Address</td>
                        <td style="padding:10px 14px;font-weight:bold;">Vendor</td>
                      </tr>
                      <tr>
                        <td style="vertical-align:top;padding:12px 14px;">
                          <div style="font-size:13px;color:#2f2f2f;line-height:1.6;">
                            {delivery_address}<br/>
                            <b>Phone:</b> {contact_phone}
                          </div>
                        </td>
                        <td style="vertical-align:top;padding:12px 14px;">
                          <div style="font-size:13px;color:#2f2f2f;line-height:1.6;">
                            <b>{vendor.get('name') or '-'}</b><br/>
                            {vendor.get('address') or '-'}<br/>
                            <b>Region:</b> {vendor.get('region') or '-'}<br/>
                            <b>Email:</b> {vendor.get('email') or '-'}<br/>
                            <b>Phone:</b> {vendor.get('phone') or '-'}
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <tr>
                  <td style="background:#F8FFFC;padding:14px 24px;text-align:center;border-top:1px solid #e9f3f0;">
                    <p style="margin:0;color:#2e7d73;font-weight:bold;">Thank you for supporting local vendors!</p>
                    <p style="margin:4px 0 0 0;color:#00695C;font-weight:bold;">— Team VoloBlink</p>
                  </td>
                </tr>
              </table>

              <div style="max-width:760px;color:#888888;font-size:11px;margin:12px auto 0 auto;text-align:center;">
                This is an automated email for your order confirmation. For support, contact connect@projectdevops.in
              </div>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    # If user email missing for some reason, still notify admins
    recipients = [email_to] if email_to else ADMIN_CC
    cc = ADMIN_CC if email_to else []

    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        cc=cc,
        body=body,
        subtype="html",
    )
    fm = FastMail(conf)
    await fm.send_message(message)
