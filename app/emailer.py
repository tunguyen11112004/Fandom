from app.config import settings


def send_mail(to_email: str, subject: str, body: str, html: str | None = None) -> None:
    if settings.email_backend == "smtp" and settings.smtp_host:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.set_content(body)
        if html:
            msg.add_alternative(html, subtype="html")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, (settings.smtp_password or "").replace(" ", ""))
            smtp.send_message(msg)
        return

    def _out(text: str) -> None:
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode("ascii", "replace").decode("ascii"))

    _out("\n===== EMAIL (dev console) =====")
    _out(f"To: {to_email}")
    _out(f"Subject: {subject}")
    _out(body)
    _out("===== END EMAIL =====\n")


def send_verify_email(to_email: str, raw_token: str) -> None:
    link = f"{settings.public_base_url}/verify/{raw_token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;color:#1a120c;line-height:1.5">
      <p>Confirm this address for Fan Hub Plus.</p>
      <p>
        <a href="{link}" style="display:inline-block;background:#1a120c;color:#f6f1e6;text-decoration:none;border-radius:999px;padding:12px 22px;font-weight:600">Confirm email</a>
      </p>
      <p>The button expires in {settings.email_verify_hours} hours.</p>
    </div>
    """
    send_mail(
        to_email,
        "Confirm your Fan Hub Plus email",
        "Confirm your Fan Hub Plus email with the button in this message. It expires in "
        f"{settings.email_verify_hours} hours.",
        html,
    )


def send_moderation_email(to_email: str, title: str, decision: str, reason: str | None = None) -> None:
    extra = f"\nReason: {reason}" if reason else ""
    send_mail(
        to_email,
        f"Moderation result: {title}",
        f"Bài \"{title}\" was {decision}.{extra}\n",
    )


def send_reset_otp_email(to_email: str, code: str) -> None:
    html = f"""
    <div style="font-family:Arial,sans-serif;color:#1a120c;line-height:1.5">
      <p>Your Fan Hub Plus password code is</p>
      <p style="font-size:32px;letter-spacing:0.28em;font-weight:700">{code}</p>
      <p>It expires in {settings.password_reset_minutes} minutes and works once.</p>
    </div>
    """
    send_mail(
        to_email,
        "Your Fan Hub Plus password code",
        f"Your Fan Hub Plus password code is {code}. It expires in {settings.password_reset_minutes} minutes.",
        html,
    )


def send_reset_email(to_email: str, raw_token: str) -> None:
    link = f"{settings.public_base_url}/reset/{raw_token}"
    send_mail(
        to_email,
        "Reset your Fan Hub Plus password",
        f"Open this link to reset your password (expires in {settings.password_reset_minutes} minutes):\n{link}\n",
    )
