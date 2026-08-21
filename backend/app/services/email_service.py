"""
Email Notification Service
──────────────────────────
Sends automated screening result emails via SMTP.

Verdict → Template:
  ≥ 70  (ACCEPT) → "Congratulations — you've been shortlisted"
  40-70 (REVIEW) → "Your application is under review"
  < 40  (REJECT) → "Thank you for applying"

Config (add to .env):
  SMTP_HOST     = smtp.gmail.com
  SMTP_PORT     = 587
  SMTP_USER     = your@gmail.com
  SMTP_PASS     = your_app_password    (Gmail App Password — not your login password)
  FROM_EMAIL    = noreply@ai-ats.com
  EMAIL_ENABLED = true
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from ..core.config import settings
from ..core.logger import log


# ─── HTML templates ───────────────────────────────────────────────────────────

def _build_html(
    candidate_name: str,
    job_title: str,
    verdict: str,        # accept | review | reject
    score: float,
    suggestions: list,
    company_name: str = "AI Recruitment Platform",
) -> str:
    score_pct = round(score)

    if verdict == "accept":
        header_color = "#10b981"
        header_bg    = "#052e16"
        verdict_text = "🎉 Congratulations — You've Been Shortlisted!"
        body_text    = (
            f"We reviewed your application for <strong>{job_title}</strong> "
            f"and are excited to inform you that your profile has been <strong>shortlisted</strong> "
            f"for the next round. Our team will reach out to schedule an interview shortly."
        )
        cta_text  = "Prepare for Your Interview"
        cta_color = "#10b981"

    elif verdict == "review":
        header_color = "#f59e0b"
        header_bg    = "#292400"
        verdict_text = "📋 Your Application Is Under Review"
        body_text    = (
            f"Thank you for applying to <strong>{job_title}</strong>. "
            f"Your application is currently under review by our hiring team. "
            f"We'll get back to you within 5–7 business days."
        )
        cta_text  = "View Application Tips"
        cta_color = "#f59e0b"

    else:  # reject
        header_color = "#6b7280"
        header_bg    = "#111827"
        verdict_text = "Thank You for Applying"
        body_text    = (
            f"Thank you for your interest in <strong>{job_title}</strong>. "
            f"After careful review, we've decided to move forward with other candidates "
            f"whose experience more closely matches our current needs. "
            f"We encourage you to apply for future openings."
        )
        cta_text  = "Browse Other Opportunities"
        cta_color = "#3b82f6"

    suggestions_html = ""
    if suggestions and verdict != "accept":
        items = "".join(f"<li style='margin-bottom:8px;color:#94a3b8;'>{s}</li>" for s in suggestions[:3])
        suggestions_html = f"""
        <div style="margin:24px 0;padding:20px;background:#0f172a;border-radius:12px;border:1px solid #1e293b;">
          <p style="color:#64748b;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin:0 0 12px;">Resume Improvement Tips</p>
          <ul style="margin:0;padding-left:20px;">{items}</ul>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0a0a0b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:600px;margin:0 auto;padding:40px 20px;">

    <!-- Header -->
    <div style="background:{header_bg};border:1px solid {header_color}30;border-radius:20px 20px 0 0;padding:40px;text-align:center;">
      <div style="width:64px;height:64px;background:{header_color}20;border:2px solid {header_color}40;border-radius:16px;display:inline-flex;align-items:center;justify-content:center;margin-bottom:16px;">
        <span style="font-size:28px;">{'✓' if verdict=='accept' else ('◎' if verdict=='review' else '○')}</span>
      </div>
      <h1 style="color:{header_color};font-size:22px;font-weight:800;margin:0 0 8px;">{verdict_text}</h1>
      <p style="color:#475569;font-size:14px;margin:0;">{company_name}</p>
    </div>

    <!-- Body -->
    <div style="background:#0f172a;border:1px solid #1e293b;border-top:none;border-radius:0 0 20px 20px;padding:40px;">
      <p style="color:#e2e8f0;font-size:16px;margin:0 0 8px;">Hi <strong style="color:white;">{candidate_name}</strong>,</p>
      <p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:16px 0;">{body_text}</p>

      <!-- Score badge -->
      <div style="text-align:center;margin:28px 0;">
        <div style="display:inline-block;background:#1e293b;border:1px solid #334155;border-radius:100px;padding:12px 28px;">
          <span style="color:#64748b;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">ATS Match Score</span><br>
          <span style="color:{header_color};font-size:36px;font-weight:900;line-height:1.2;">{score_pct}%</span>
        </div>
      </div>

      {suggestions_html}

      <!-- CTA -->
      <div style="text-align:center;margin:28px 0 0;">
        <a href="#" style="display:inline-block;background:{cta_color};color:white;font-weight:700;font-size:14px;padding:14px 32px;border-radius:12px;text-decoration:none;">{cta_text} →</a>
      </div>
    </div>

    <!-- Footer -->
    <p style="text-align:center;color:#374151;font-size:12px;margin-top:24px;">
      This is an automated message from {company_name}.<br>
      You are receiving this because you applied for <em>{job_title}</em>.
    </p>
  </div>
</body>
</html>
"""


# ─── Sender ───────────────────────────────────────────────────────────────────

class EmailService:
    @staticmethod
    def _is_configured() -> bool:
        return bool(
            getattr(settings, "SMTP_HOST", "")
            and getattr(settings, "SMTP_USER", "")
            and getattr(settings, "SMTP_PASS", "")
            and getattr(settings, "EMAIL_ENABLED", "false").lower() == "true"
        )

    @staticmethod
    def send_screening_result(
        to_email: str,
        candidate_name: str,
        job_title: str,
        score: float,
        verdict: str,
        suggestions: list | None = None,
    ) -> bool:
        """
        Send a screening result email.
        Returns True on success, False if disabled or on error.
        """
        if not EmailService._is_configured():
            log.info(
                "email_service.disabled",
                note="Set SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_ENABLED=true to enable emails."
            )
            return False

        try:
            msg = MIMEMultipart("alternative")
            subject_map = {
                "accept": f"🎉 You've been shortlisted — {job_title}",
                "review": f"📋 Application Update — {job_title}",
                "reject": f"Thank you for applying — {job_title}",
            }
            msg["Subject"] = subject_map.get(verdict, f"Application Update — {job_title}")
            msg["From"]    = getattr(settings, "FROM_EMAIL", settings.SMTP_USER)
            msg["To"]      = to_email

            html = _build_html(
                candidate_name=candidate_name or "Candidate",
                job_title=job_title,
                verdict=verdict,
                score=score,
                suggestions=suggestions or [],
            )
            msg.attach(MIMEText(html, "html"))

            context = ssl.create_default_context()
            port = int(getattr(settings, "SMTP_PORT", 587))

            with smtplib.SMTP(settings.SMTP_HOST, port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.sendmail(msg["From"], to_email, msg.as_string())

            log.info("email_service.sent", to=to_email, verdict=verdict, score=score)
            return True

        except Exception as e:
            log.error("email_service.error", to=to_email, error=str(e))
            return False

    @staticmethod
    def send_interview_scheduled(
        to_email: str,
        candidate_name: str,
        job_title: str,
        scheduled_at,
        location: Optional[str] = None,
        meeting_link: Optional[str] = None,
    ) -> bool:
        """Send an interview schedule confirmation email."""
        if not EmailService._is_configured():
            log.info("email_service.disabled", note="EMAIL_ENABLED not set.")
            return False

        try:
            date_str = (
                scheduled_at.strftime("%A, %B %d, %Y at %I:%M %p UTC")
                if scheduled_at else "TBD"
            )
            location_line = f"<p style='color:#94a3b8;margin:4px 0;'>📍 <strong>Location:</strong> {location}</p>" if location else ""
            link_line = (
                f"<p style='margin:4px 0;'><a href='{meeting_link}' style='color:#6366f1;'>🔗 Join Meeting</a></p>"
                if meeting_link else ""
            )

            html = f"""
            <!DOCTYPE html><html><head><meta charset="utf-8"></head>
            <body style="font-family:-apple-system,sans-serif;background:#0a0a0b;margin:0;padding:40px 0;">
              <div style="max-width:560px;margin:0 auto;background:#0f172a;border-radius:16px;overflow:hidden;border:1px solid #1e293b;">
                <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:32px;text-align:center;">
                  <h1 style="color:#fff;margin:0;font-size:20px;font-weight:700;">Interview Scheduled</h1>
                </div>
                <div style="padding:32px;">
                  <p style="color:#e2e8f0;margin:0 0 20px;">An interview has been confirmed:</p>
                  <div style="background:#1e293b;border-radius:10px;padding:20px;border:1px solid #334155;">
                    <p style="color:#fff;font-size:16px;font-weight:600;margin:0 0 10px;">👤 {candidate_name}</p>
                    <p style="color:#94a3b8;margin:4px 0;">💼 <strong>Role:</strong> {job_title}</p>
                    <p style="color:#94a3b8;margin:4px 0;">📅 <strong>When:</strong> {date_str}</p>
                    {location_line}
                    {link_line}
                  </div>
                  <p style="color:#475569;font-size:12px;margin-top:20px;">This is an automated message from AI Talent Cloud.</p>
                </div>
              </div>
            </body></html>
            """

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Interview Scheduled: {candidate_name} — {job_title}"
            msg["From"] = getattr(settings, "FROM_EMAIL", settings.SMTP_USER)
            msg["To"] = to_email
            msg.attach(MIMEText(html, "html"))

            context = ssl.create_default_context()
            port = int(getattr(settings, "SMTP_PORT", 587))
            with smtplib.SMTP(settings.SMTP_HOST, port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.sendmail(msg["From"], to_email, msg.as_string())

            log.info("email_service.interview_scheduled", to=to_email, candidate=candidate_name)
            return True
        except Exception as e:
            log.error("email_service.interview_scheduled.error", to=to_email, error=str(e))
            return False

    @staticmethod
    def send_email_raw(to_email: str, subject: str, html_body: str) -> bool:
        """Generic low-level send for custom HTML emails."""
        if not EmailService._is_configured():
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = getattr(settings, "FROM_EMAIL", settings.SMTP_USER)
            msg["To"] = to_email
            msg.attach(MIMEText(html_body, "html"))
            context = ssl.create_default_context()
            port = int(getattr(settings, "SMTP_PORT", 587))
            with smtplib.SMTP(settings.SMTP_HOST, port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.sendmail(msg["From"], to_email, msg.as_string())
            return True
        except Exception as e:
            log.error("email_service.raw.error", to=to_email, error=str(e))
            return False
