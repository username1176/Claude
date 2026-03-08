"""SendGrid email tasks for premium subscriber notifications.

Weekly report emails, subscription confirmations, and prediction alerts
are sent via SendGrid transactional email.
"""

import logging
import os
from datetime import datetime, timezone

from celery import shared_task

logger = logging.getLogger(__name__)


def _send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an email via SendGrid.

    Returns True on success, False on failure.
    """
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    from_email = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@genomeinsight.app")

    if not api_key:
        logger.warning("SENDGRID_API_KEY not set — email not sent to %s", to_email)
        return False

    try:
        import sendgrid
        from sendgrid.helpers.mail import Content, Email, Mail, To

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        message = Mail(
            from_email=Email(from_email, "GenomeInsight"),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content),
        )
        response = sg.client.mail.send.post(request_body=message.get())
        logger.info("Email sent to %s — status %s", to_email, response.status_code)
        return 200 <= response.status_code < 300
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def _build_report_email(user_email: str, report) -> str:
    """Build HTML email body for a weekly healthspan report."""
    scores = []
    if report.overall_score is not None:
        scores.append(f"Overall: {report.overall_score:.0f}/100")
    if report.sleep_score is not None:
        scores.append(f"Sleep: {report.sleep_score:.0f}")
    if report.activity_score is not None:
        scores.append(f"Activity: {report.activity_score:.0f}")
    if report.stress_score is not None:
        scores.append(f"Stress: {report.stress_score:.0f}")

    scores_html = "".join(f"<li>{s}</li>" for s in scores)
    innerage_line = ""
    if report.innerage_snapshot is not None:
        innerage_line = f"<p><strong>InnerAge snapshot:</strong> {report.innerage_snapshot:.1f}</p>"

    return f"""
    <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; color: #3A3632;">
      <div style="background: linear-gradient(135deg, #F5F5F0, #FAFAF7); padding: 32px; border-radius: 8px;">
        <h2 style="color: #5C4B3F; margin-bottom: 4px;">Your Weekly Healthspan Report</h2>
        <p style="color: #7A7267; font-size: 14px;">
          {report.period_start} — {report.period_end}
        </p>
        <hr style="border: none; border-top: 1px solid rgba(92,75,63,0.1); margin: 16px 0;" />
        <ul style="list-style: none; padding: 0; font-size: 15px;">
          {scores_html}
        </ul>
        {innerage_line}
        <p style="margin-top: 24px;">
          <a href="{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/healthspan"
             style="background: #5C4B3F; color: #FAFAF7; padding: 10px 24px; border-radius: 6px;
                    text-decoration: none; font-size: 14px;">
            View Full Report
          </a>
        </p>
      </div>
      <p style="font-size: 11px; color: #A8A8A8; text-align: center; margin-top: 24px;">
        GenomeInsight — Predictions are estimates based on statistical models.
        Always consult a healthcare professional.
      </p>
    </div>
    """


@shared_task(bind=True, name="app.tasks.email_tasks.send_weekly_report_emails")
def send_weekly_report_emails(self):
    """Send weekly healthspan report emails to all premium subscribers."""
    from app.extensions import db
    from app.models.subscription import Subscription
    from app.models.healthspan import HealthspanReport
    from app.models.user import User

    premium_subs = Subscription.query.filter_by(tier="premium", status="active").all()
    sent = 0
    for sub in premium_subs:
        user = db.session.get(User, sub.user_id)
        if not user:
            continue

        report = (
            HealthspanReport.query
            .filter_by(user_id=sub.user_id)
            .order_by(HealthspanReport.generated_at.desc())
            .first()
        )
        if not report:
            continue

        html = _build_report_email(user.email, report)
        if _send_email(user.email, "Your Weekly Healthspan Report — GenomeInsight", html):
            sent += 1

    logger.info("Sent %d weekly report emails to premium subscribers", sent)
    return {"sent": sent, "total_premium": len(premium_subs)}


@shared_task(bind=True, name="app.tasks.email_tasks.send_subscription_confirmation")
def send_subscription_confirmation(self, user_id: str, tier: str):
    """Send subscription confirmation email."""
    from app.extensions import db
    from app.models.user import User

    user = db.session.get(User, user_id)
    if not user:
        return

    html = f"""
    <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; color: #3A3632;">
      <div style="background: linear-gradient(135deg, #F5F5F0, #FAFAF7); padding: 32px; border-radius: 8px;">
        <h2 style="color: #5C4B3F;">Welcome to {tier.title()}</h2>
        <p>Thank you for upgrading your GenomeInsight membership.</p>
        <p>Your {tier} plan includes:</p>
        <ul style="font-size: 14px; line-height: 1.8;">
          {"<li>AI Health Chat</li><li>InnerAge biological age tracking</li><li>Predictive biomarker trends</li><li>Weekly healthspan reports</li><li>Priority support</li>" if tier == "premium" else "<li>Extended upload limits</li><li>Biomarker optimized zones</li><li>Full blood panel history</li>"}
        </ul>
        <p style="margin-top: 16px;">
          <a href="{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/"
             style="background: #5C4B3F; color: #FAFAF7; padding: 10px 24px; border-radius: 6px;
                    text-decoration: none; font-size: 14px;">
            Go to Dashboard
          </a>
        </p>
      </div>
      <p style="font-size: 11px; color: #A8A8A8; text-align: center; margin-top: 24px;">
        GenomeInsight — For informational purposes only. Not medical advice.
      </p>
    </div>
    """
    _send_email(user.email, f"Welcome to GenomeInsight {tier.title()}", html)


@shared_task(bind=True, name="app.tasks.email_tasks.send_prediction_alert")
def send_prediction_alert(self, user_id: str, marker_name: str, trend_direction: str, days_to_out: int | None):
    """Alert premium subscribers when a biomarker prediction shows concerning trend."""
    from app.extensions import db
    from app.models.user import User
    from app.models.subscription import Subscription

    user = db.session.get(User, user_id)
    if not user:
        return

    sub = Subscription.query.filter_by(user_id=user_id).first()
    if not sub or not sub.is_premium:
        return

    urgency = ""
    if days_to_out and days_to_out < 30:
        urgency = f" (predicted to leave optimal range in ~{days_to_out} days)"

    html = f"""
    <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; color: #3A3632;">
      <div style="background: linear-gradient(135deg, #F5F5F0, #FAFAF7); padding: 32px; border-radius: 8px;">
        <h2 style="color: #5C4B3F;">Biomarker Alert</h2>
        <p><strong>{marker_name}</strong> shows a <strong>{trend_direction}</strong> trend{urgency}.</p>
        <p style="color: #7A7267; font-size: 14px;">
          This is a statistical prediction based on your historical data. Please consult
          your healthcare provider for personalized guidance.
        </p>
        <p style="margin-top: 16px;">
          <a href="{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/healthspan"
             style="background: #5C4B3F; color: #FAFAF7; padding: 10px 24px; border-radius: 6px;
                    text-decoration: none; font-size: 14px;">
            View Predictions
          </a>
        </p>
      </div>
      <p style="font-size: 11px; color: #A8A8A8; text-align: center; margin-top: 24px;">
        Predictions are estimates based on statistical models and may not reflect
        actual future outcomes. Always consult a healthcare professional.
      </p>
    </div>
    """
    _send_email(user.email, f"GenomeInsight Alert: {marker_name} Trend", html)
