"""DepScope transactional email templates.

All public builders return a tuple ``(subject, html, plain_text)`` ready to be
passed to :func:`api.mailer.send_email`. Every template is designed to look
good in dark mode (default) with a graceful fallback for light clients; HTML
bodies are inlined, table-based, and multipart-paired with a legible plain
text alternative.
"""
from __future__ import annotations

import html as _html
from typing import Optional, Tuple


BRAND = {
    "name": "DepScope",
    "url": "https://depscope.dev",
    "from_name": "DepScope",
    "from_email": "depscope@cuttalo.com",
    "support": "depscope@cuttalo.com",
}

COLORS = {
    "bg": "#09090b",
    "card": "#18181b",
    "border": "#27272a",
    "text": "#fafafa",
    "text_dim": "#a1a1aa",
    "text_faded": "#71717a",
    "accent": "#fbbf24",
    "accent_dim": "#f59e0b",
    "green": "#10b981",
    "red": "#ef4444",
}


# ---------------------------------------------------------------------------
# Base layout
# ---------------------------------------------------------------------------

def _base_html(title: str, preheader: str, content_html: str) -> str:
    """Render a full HTML email wrapping ``content_html`` in brand chrome.

    ``content_html`` is inserted as-is inside the main card; callers are
    responsible for escaping any user-supplied text placed inside it.
    """
    safe_title = _html.escape(title)
    safe_pre = _html.escape(preheader)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<meta name="supported-color-schemes" content="dark light">
<title>{safe_title}</title>
</head>
<body style="margin:0;padding:0;background:{COLORS['bg']};color:{COLORS['text']};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;font-size:15px;line-height:1.6;">
  <span style="display:none;max-height:0;overflow:hidden;visibility:hidden;opacity:0;color:transparent;">{safe_pre}</span>
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:{COLORS['bg']};">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:560px;">
          <tr>
            <td style="padding-bottom:32px;">
              <a href="{BRAND['url']}" style="text-decoration:none;font-family:'SF Mono','JetBrains Mono',Menlo,Consolas,monospace;font-size:18px;font-weight:700;color:{COLORS['text']};">
                <span style="color:{COLORS['accent']};">dep</span>scope
              </a>
            </td>
          </tr>
          <tr>
            <td style="background:{COLORS['card']};border:1px solid {COLORS['border']};border-radius:8px;padding:32px;">
              {content_html}
            </td>
          </tr>
          <tr>
            <td style="padding:32px 0 0 0;">
              <p style="margin:0 0 8px 0;font-size:12px;color:{COLORS['text_faded']};">
                {BRAND['name']} &middot; <a href="{BRAND['url']}" style="color:{COLORS['text_faded']};text-decoration:underline;">depscope.dev</a>
              </p>
              <p style="margin:0;font-size:12px;color:{COLORS['text_faded']};">
                <a href="{BRAND['url']}/privacy" style="color:{COLORS['text_faded']};text-decoration:underline;">Privacy</a>
                &middot; <a href="mailto:{BRAND['support']}" style="color:{COLORS['text_faded']};text-decoration:underline;">Contact</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _button(label: str, url: str) -> str:
    return f"""
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0;">
        <tr>
          <td style="border-radius:6px;background:{COLORS['accent']};box-shadow:0 1px 3px rgba(0,0,0,0.3);">
            <a href="{_html.escape(url)}" style="display:inline-block;padding:12px 24px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:14px;font-weight:600;color:#000;text-decoration:none;border-radius:6px;">{_html.escape(label)}</a>
          </td>
        </tr>
      </table>
    """


# ---------------------------------------------------------------------------
# Email types
# ---------------------------------------------------------------------------

def magic_link_email(email: str, link: str, ip: Optional[str] = None) -> Tuple[str, str, str]:
    """Build the magic link sign-in email (subject, html, plain)."""
    subject = "Your DepScope sign-in link"
    preheader = "Click the button to sign in. Link expires in 15 minutes."
    safe_link = _html.escape(link)
    ip_row = ""
    if ip:
        ip_row = (
            f"<br><br>Requested from IP: "
            f"<span style=\"font-family:'SF Mono','JetBrains Mono',Menlo,monospace;color:{COLORS['text_dim']};\">{_html.escape(ip)}</span>"
        )
    content = f"""
      <h1 style="margin:0 0 16px 0;font-size:20px;font-weight:600;color:{COLORS['text']};">Sign in to DepScope</h1>
      <p style="margin:0 0 8px 0;color:{COLORS['text_dim']};">
        Click the button below to sign in. This link expires in 15 minutes and can only be used once.
      </p>
      {_button('Sign in to DepScope', link)}
      <p style="margin:0 0 8px 0;font-size:12px;color:{COLORS['text_faded']};">Or copy this link into your browser:</p>
      <p style="margin:0 0 8px 0;font-family:'SF Mono','JetBrains Mono',Menlo,monospace;font-size:12px;word-break:break-all;color:{COLORS['accent']};">{safe_link}</p>
      <hr style="border:none;border-top:1px solid {COLORS['border']};margin:24px 0;">
      <p style="margin:0;font-size:12px;color:{COLORS['text_faded']};">
        Didn&rsquo;t request this? You can safely ignore this email &mdash; nobody accesses your account without the link.{ip_row}
      </p>
    """
    html = _base_html(subject, preheader, content)
    plain = f"""Sign in to DepScope

Click the link below to sign in. This link expires in 15 minutes and can only be used once.

{link}

Didn't request this? You can safely ignore this email.
{('Requested from IP: ' + ip) if ip else ''}

—
DepScope · {BRAND['url']}
Privacy: {BRAND['url']}/privacy · Contact: {BRAND['support']}
"""
    return subject, html, plain


def welcome_email(email: str) -> Tuple[str, str, str]:
    """First-login welcome email."""
    subject = "Welcome to DepScope"
    preheader = "Your account is ready. Here is what you can do next."
    curl_example = _html.escape(
        'curl https://depscope.dev/api/check/npm/express \\\n'
        '  -H "Authorization: Bearer ds_live_xxx"'
    )
    content = f"""
      <h1 style="margin:0 0 12px 0;font-size:20px;font-weight:600;">Welcome to DepScope</h1>
      <p style="margin:0 0 20px 0;color:{COLORS['text_dim']};">
        Your account is ready. You now get a higher rate limit (1,000 req/min vs 200 for anonymous calls) and access to the dashboard.
      </p>

      <h2 style="margin:24px 0 8px 0;font-size:14px;font-weight:600;color:{COLORS['text']};letter-spacing:0.02em;">Create an API key</h2>
      <p style="margin:0 0 12px 0;color:{COLORS['text_dim']};">
        Generate live and test keys from your dashboard, then plug them into your AI agent configuration.
      </p>
      <pre style="margin:0 0 16px 0;background:{COLORS['bg']};border:1px solid {COLORS['border']};border-radius:6px;padding:12px;font-family:'SF Mono','JetBrains Mono',Menlo,monospace;font-size:12px;line-height:1.5;color:{COLORS['accent']};overflow-x:auto;white-space:pre;">{curl_example}</pre>

      <h2 style="margin:24px 0 8px 0;font-size:14px;font-weight:600;color:{COLORS['text']};letter-spacing:0.02em;">What DepScope covers</h2>
      <ul style="margin:0 0 16px 0;padding-left:20px;color:{COLORS['text_dim']};">
        <li>Package health across 17 ecosystems (npm, PyPI, Cargo, Go, Maven, NuGet, and more)</li>
        <li>Error &rarr; fix resolution database</li>
        <li>Stack compatibility matrix</li>
        <li>Known bugs by package version</li>
        <li>MCP server for Claude Code, Cursor and Windsurf</li>
      </ul>

      {_button('Open dashboard', 'https://depscope.dev/dashboard')}
    """
    html = _base_html(subject, preheader, content)
    plain = f"""Welcome to DepScope

Your account is ready. You now have a higher rate limit (1,000 req/min vs 200 for anonymous calls) and access to the dashboard.

Create an API key:
  https://depscope.dev/dashboard

Quick example:
  curl https://depscope.dev/api/check/npm/express \\
    -H "Authorization: Bearer ds_live_xxx"

What DepScope covers:
  - Package health across 17 ecosystems
  - Error -> fix resolution database
  - Stack compatibility matrix
  - Known bugs by package version
  - MCP server for Claude Code, Cursor and Windsurf

—
DepScope · {BRAND['url']}
Privacy: {BRAND['url']}/privacy · Contact: {BRAND['support']}
"""
    return subject, html, plain


def api_key_created_email(
    email: str,
    key_name: str,
    key_prefix: str,
    is_test: bool,
) -> Tuple[str, str, str]:
    """Transactional notification sent when a new API key is created."""
    env_label = "Test" if is_test else "Live"
    subject = f"New {env_label.lower()} API key created"
    preheader = f"A new {env_label.lower()} API key '{key_name}' was created on your account."
    prefix_display = f"{_html.escape(key_prefix)}&hellip;"

    content = f"""
      <h1 style="margin:0 0 12px 0;font-size:20px;font-weight:600;">New API key created</h1>
      <p style="margin:0 0 20px 0;color:{COLORS['text_dim']};">
        A new {env_label.lower()} API key was just created on your DepScope account.
      </p>

      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:{COLORS['bg']};border:1px solid {COLORS['border']};border-radius:6px;margin:0 0 20px 0;">
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid {COLORS['border']};font-size:12px;color:{COLORS['text_faded']};">Name</td>
          <td align="right" style="padding:12px 16px;border-bottom:1px solid {COLORS['border']};font-size:13px;color:{COLORS['text']};">{_html.escape(key_name)}</td>
        </tr>
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid {COLORS['border']};font-size:12px;color:{COLORS['text_faded']};">Prefix</td>
          <td align="right" style="padding:12px 16px;border-bottom:1px solid {COLORS['border']};font-family:'SF Mono','JetBrains Mono',Menlo,monospace;font-size:13px;color:{COLORS['accent']};">{prefix_display}</td>
        </tr>
        <tr>
          <td style="padding:12px 16px;font-size:12px;color:{COLORS['text_faded']};">Environment</td>
          <td align="right" style="padding:12px 16px;font-size:13px;color:{COLORS['text']};">{env_label}</td>
        </tr>
      </table>

      {_button('Manage API keys', 'https://depscope.dev/dashboard')}

      <p style="margin:16px 0 0 0;font-size:13px;color:{COLORS['text_faded']};">
        If you didn&rsquo;t create this key,
        <a href="https://depscope.dev/dashboard" style="color:{COLORS['red']};text-decoration:underline;">revoke it immediately</a>.
      </p>
    """
    html = _base_html(subject, preheader, content)
    plain = f"""New {env_label.lower()} API key created

Name:        {key_name}
Prefix:      {key_prefix}...
Environment: {env_label}

Manage keys: https://depscope.dev/dashboard

If you didn't create this key, revoke it immediately from the dashboard.

—
DepScope · {BRAND['url']}
Privacy: {BRAND['url']}/privacy · Contact: {BRAND['support']}
"""
    return subject, html, plain


# ---------------------------------------------------------------------------
# Stubs reserved for future use
# ---------------------------------------------------------------------------

def alert_email(issue: str, details: str) -> Tuple[str, str, str]:
    """Internal security/ops alert. Not wired to any endpoint yet."""
    subject = f"[DepScope] Alert: {issue}"
    preheader = issue
    content = f"""
      <h1 style="margin:0 0 12px 0;font-size:20px;font-weight:600;color:{COLORS['red']};">Alert: {_html.escape(issue)}</h1>
      <p style="margin:0 0 16px 0;color:{COLORS['text_dim']};">An automated alert was triggered.</p>
      <pre style="margin:0;background:{COLORS['bg']};border:1px solid {COLORS['border']};border-radius:6px;padding:12px;font-family:'SF Mono','JetBrains Mono',Menlo,monospace;font-size:12px;color:{COLORS['text']};overflow-x:auto;white-space:pre-wrap;">{_html.escape(details)}</pre>
    """
    html = _base_html(subject, preheader, content)
    plain = f"""ALERT: {issue}

{details}

—
DepScope · {BRAND['url']}
"""
    return subject, html, plain


def weekly_digest_email(user_email: str, stats: dict) -> Tuple[str, str, str]:
    """Weekly usage digest. Reserved for a future scheduled job."""
    subject = "Your DepScope weekly digest"
    preheader = "A snapshot of your API usage over the last 7 days."
    calls = int(stats.get("calls", 0))
    pkgs = int(stats.get("packages", 0))
    top = stats.get("top_package") or "—"
    content = f"""
      <h1 style="margin:0 0 12px 0;font-size:20px;font-weight:600;">Your weekly digest</h1>
      <p style="margin:0 0 20px 0;color:{COLORS['text_dim']};">Here is a snapshot of your DepScope activity over the last 7 days.</p>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:{COLORS['bg']};border:1px solid {COLORS['border']};border-radius:6px;margin:0 0 20px 0;">
        <tr><td style="padding:12px 16px;border-bottom:1px solid {COLORS['border']};font-size:12px;color:{COLORS['text_faded']};">API calls</td><td align="right" style="padding:12px 16px;border-bottom:1px solid {COLORS['border']};font-size:13px;color:{COLORS['text']};">{calls:,}</td></tr>
        <tr><td style="padding:12px 16px;border-bottom:1px solid {COLORS['border']};font-size:12px;color:{COLORS['text_faded']};">Unique packages</td><td align="right" style="padding:12px 16px;border-bottom:1px solid {COLORS['border']};font-size:13px;color:{COLORS['text']};">{pkgs:,}</td></tr>
        <tr><td style="padding:12px 16px;font-size:12px;color:{COLORS['text_faded']};">Top package</td><td align="right" style="padding:12px 16px;font-family:'SF Mono','JetBrains Mono',Menlo,monospace;font-size:13px;color:{COLORS['accent']};">{_html.escape(str(top))}</td></tr>
      </table>
      {_button('Open dashboard', 'https://depscope.dev/dashboard')}
    """
    html = _base_html(subject, preheader, content)
    plain = f"""Your DepScope weekly digest

API calls:       {calls:,}
Unique packages: {pkgs:,}
Top package:     {top}

Dashboard: https://depscope.dev/dashboard

—
DepScope · {BRAND['url']}
"""
    return subject, html, plain
