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
    link = f"{settings.public_base_url}{settings.api_prefix}/auth/verify-email?token={raw_token}"
    send_mail(
        to_email,
        "Xác minh email Fan Hub Plus",
        f"Mở liên kết để kích hoạt tài khoản (hết hạn {settings.email_verify_hours} giờ):\n{link}\n",
    )


def send_moderation_email(to_email: str, title: str, decision: str, reason: str | None = None) -> None:
    extra = f"\nLý do: {reason}" if reason else ""
    send_mail(
        to_email,
        f"Kết quả kiểm duyệt: {title}",
        f"Bài \"{title}\" đã được {decision}.{extra}\n",
    )


def send_reset_email(to_email: str, raw_token: str) -> None:
    link = f"{settings.public_base_url}{settings.api_prefix}/auth/reset-password?token={raw_token}"
    send_mail(
        to_email,
        "Đặt lại mật khẩu Fan Hub Plus",
        f"Mở liên kết để đặt lại mật khẩu (hết hạn {settings.password_reset_minutes} phút):\n{link}\n",
    )
