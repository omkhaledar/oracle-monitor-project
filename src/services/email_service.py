import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from datetime import datetime

from src.config import AppConfig

logger = logging.getLogger(__name__)

class EmailService:
    """Handles sending email reports."""

    def __init__(self, config: AppConfig):
        self.config = config.email

    def _format_html_report(self, summary_data: Dict[str, Any], timestamp: datetime) -> str:
        """Formats the analysis summary into a professional HTML report."""
        
        header = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; }}
                h1 {{ color: #2c3e50; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; font-weight: bold; }}
                .summary-p {{ font-size: 1.1em; }}
                .critical {{ color: #ef4444; font-weight: bold; }}
                .high {{ color: #f97316; font-weight: bold; }}
                .medium {{ color: #f59e0b; }}
            </style>
        </head>
        <body>
            <h1>Oracle Alert Log - AI Summary Report</h1>
            <p><strong>Report Timestamp:</strong> {timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            <p class="summary-p">
                Found <strong>{summary_data['total_errors']}</strong> new errors across 
                <strong>{summary_data['servers_with_errors']}</strong> of 
                <strong>{summary_data['total_servers']}</strong> monitored servers.
            </p>
        """

        table = """
            <table>
                <thead>
                    <tr>
                        <th>Server Name</th>
                        <th>Total Errors</th>
                        <th>Critical</th>
                        <th>High</th>
                        <th>Medium</th>
                    </tr>
                </thead>
                <tbody>
        """
        for server in summary_data['servers']:
            crit = server['criticality']
            table += f"""
                    <tr>
                        <td>{server['name']}</td>
                        <td>{server['error_count']}</td>
                        <td class="critical">{crit.get('Critical', 0)}</td>
                        <td class="high">{crit.get('High', 0)}</td>
                        <td class="medium">{crit.get('Medium', 0)}</td>
                    </tr>
            """
        
        # --- UPDATED FOOTER WITH STYLED BUTTON ---
        footer = """
                </tbody>
            </table>
            <p style="margin-top: 20px; font-size: 0.9em; color: #777;">
                This is an automated report. For detailed error analysis, please open the live dashboard:
            </p>
            <div style="text-align: center; margin-top: 25px; margin-bottom: 25px;">
                <a href="http://dba-logs.elsewedy.com:5001" style="background-color: #2563eb; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-size: 18px; font-weight: bold; display: inline-block;">
                    Open Live Dashboard
                </a>
            </div>
        </body></html>
        """
        return header + table + footer

    async def send_comprehensive_report(self, summary_data: Dict[str, Any], timestamp: datetime):
        """Sends a comprehensive HTML summary report via SMTP."""
        if not self.config.to_addresses:
            logger.warning("No recipient addresses configured. Skipping email report.")
            return

        subject = self.config.subject_template.format(company_name="El Sewedy Electric")
        html_body = self._format_html_report(summary_data, timestamp)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.config.from_address
        msg['To'] = ", ".join(self.config.to_addresses)
        msg.attach(MIMEText(html_body, 'html'))

        try:
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                if self.config.username and self.config.password:
                    server.login(self.config.username, self.config.password)
                
                server.sendmail(self.config.from_address, self.config.to_addresses, msg.as_string())
                logger.info(f"Email report sent successfully to {', '.join(self.config.to_addresses)}")

        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            raise

