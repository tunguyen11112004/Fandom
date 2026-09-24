from app.config import settings


def send_mail(to_email: str, subject: str, body: str) -> None:
    if settings.email_backend == "smtp" and settings.smtp_host:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
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
    send_mail(
        to_email,
        "Verify your Fan Hub Plus email",
        f"Open this link to activate your account (expires in {settings.email_verify_hours} hours):\n{link}\n",
    )


def send_moderation_email(to_email: str, title: str, decision: str, reason: str | None = None) -> None:
    extra = f"\nReason: {reason}" if reason else ""
    send_mail(
        to_email,
        f"Moderation result: {title}",
        f"Bài \"{title}\" was {decision}.{extra}\n",
    )


def send_reset_email(to_email: str, raw_token: str) -> None:
    link = f"{settings.public_base_url}/reset/{raw_token}"
    send_mail(
        to_email,
        "Reset your Fan Hub Plus password",
        f"Open this link to reset your password (expires in {settings.password_reset_minutes} minutes):\n{link}\n",
    )
