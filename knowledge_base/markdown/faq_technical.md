# PointStar FAQ — Technical Support

**Document ID:** KB-FAQ-003
**Version:** 2.0
**Last Updated:** 2026-01-15
**Category:** Technical

---

**Q1. I can't log in — I get an "invalid credentials" error.**
First, confirm Caps Lock is off and try a password reset. If your
organization uses JumpCloud as its identity provider (SSO) for Google
Workspace, GCP, Zoom, or other connected apps, log in via the JumpCloud
portal instead of the app's direct login page.

**Q2. My data isn't syncing between NetSuite and Google Workspace/GCP.**
Check Integration Settings → Sync Status for the last successful sync
timestamp and any error codes. Common causes are an expired OAuth token
(reconnect under Integrations) or a field-mapping mismatch after a NetSuite
customization or Google Workspace schema change.

**Q3. I'm hitting Google Cloud Platform API or quota limits.**
GCP quotas vary by service and project tier. Rate-limit errors return HTTP
429. Check Quotas in the GCP Console, or contact your Account Manager about
a quota increase request through PointStar as your reseller.

**Q4. Is there a status page for outages?**
For Google Workspace/GCP outages, check Google's official Workspace Status
Dashboard; for NetSuite, check Oracle's system status page. **If you are
reporting an active outage affecting your production environment, this must
be flagged for immediate human escalation** — do not wait for a
standard-priority response.

**Q5. What browsers are supported?**
Latest two versions of Chrome, Edge, Firefox, and Safari — consistent with
Google Workspace and NetSuite's own browser support policies. Internet
Explorer is not supported. Report rendering issues with your browser version
and OS.

**Q6. How do I enable two-factor authentication (2FA)?**
If your organization uses JumpCloud for SSO, enable 2FA centrally under
JumpCloud Admin → Security Settings — this applies across all connected
apps (Google Workspace, GCP, Zoom, Slack, GitHub, AWS). **Any report of
unauthorized account access or suspected compromised credentials must be
escalated immediately as a potential security incident** — support should
not attempt to resolve this via standard troubleshooting alone.

**Q7. Can I export my data?**
Google Workspace data can be exported via Google Takeout or Google Vault
(if licensed). NetSuite data exports (CSV/SuiteAnalytics) are available
under Reports → Export. Enterprise customers can request scheduled
automated exports via API.

**Q8. I think I just lost data — records disappeared after a NetSuite sync.**
This is treated as a **critical/data-loss case** and must be escalated to a
human agent immediately, per escalation policy. Do not attempt to advise the
customer on recovery steps without engineering involvement — advise them to
stop further syncs and escalate right away.

**Q9. Is there a mobile app?**
Google Workspace, NetSuite, and Zoom each provide their own official mobile
apps (iOS/Android) for their respective platforms; PointStar does not
maintain a separate unified mobile app.

**Q10. What are your support response time SLAs?**
Standard plans: next-business-day response. Enterprise/NetSuite contract
customers: 4-hour response for Critical-severity issues, 1-business-day for
Standard. Data loss, outages, and security incidents are always treated as
Critical severity.

**Q11. How do I report a bug vs. request a feature?**
Bugs in a PointStar-built integration or custom NetSuite/AppSheet workflow:
use the in-app "Report an Issue" button. For bugs in the underlying platform
itself (Google Workspace, NetSuite, Zoom, Meraki), these must be reported to
the vendor, and PointStar support can assist with filing that ticket.
Feature requests: submit via the Feedback FAQ process (KB-FAQ-004).
