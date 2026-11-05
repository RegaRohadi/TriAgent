# Nimbus Cloud — Cloud Subscription Plans & Pricing Handbook

**Document ID:** KB-PLAN-100
**Version:** 2.4
**Last Updated:** 2026-02-01
**Owner:** Revenue Operations
**Category:** Commercial Reference

> ILLUSTRATIVE DOCUMENT. Nimbus Cloud is a fictional company, and every figure
> in this handbook is invented for a technical exercise. Nothing here is a real
> price, a real service level, or a real contractual term. It exists to give a
> document-grounded agent a single, self-contained source of truth to answer
> from.

## 1. Scope of This Handbook

This handbook is the single source of truth for standard subscription pricing,
billing mechanics, storage limits, support targets and refund terms for
Nimbus Cloud-managed cloud subscriptions sold in Singapore, Malaysia and
Indonesia. It covers list pricing only. Negotiated enterprise agreements,
public-sector tenders and education pricing are governed by their own contract
schedules and are explicitly out of scope for this document.

Where a customer's signed order form conflicts with this handbook, the order
form takes precedence.

## 2. Plan Tiers and Per-Seat Pricing

All subscription plans are priced per seat, per month, in US dollars, billed to
the account owner. A seat is one named user with an active login; shared
mailboxes and resource calendars do not consume a seat.

| Plan | Price per seat / month | Minimum seats | Maximum seats |
|---|---|---|---|
| Starter | USD 6.00 | 1 | 25 |
| Business | USD 14.50 | 5 | 300 |
| Enterprise | USD 27.00 | 50 | unlimited |

The Starter plan is capped at 25 seats. An account that needs a 26th seat must
upgrade to Business; there is no exception process for exceeding the cap.

Plan upgrades take effect immediately and are prorated. Plan downgrades take
effect at the start of the next billing cycle, never mid-cycle.

## 3. Billing Cycles and the Annual Discount

The default billing cycle is monthly, charged in advance on the same calendar
day each month. Two prepayment options reduce the effective rate:

- Annual prepay: 15 percent discount off the monthly list rate, charged once
  for twelve months of service.
- Two-year prepay: 22 percent discount off the monthly list rate, charged once
  for twenty-four months of service.

Discounts apply to the per-seat subscription rate only. They never apply to
storage overage, professional services, training or one-off migration fees.

Seats added mid-cycle are prorated daily against a standard 30-day month,
regardless of the actual length of the calendar month. Seats removed mid-cycle
are not refunded; the seat stays active until the end of the paid period.

## 4. Storage Quotas and Overage Charges

Storage is pooled across the whole account rather than enforced per user, so
one heavy user does not block the rest of the organisation.

| Plan | Pooled storage allowance |
|---|---|
| Starter | 30 GB per seat |
| Business | 2 TB per seat |
| Enterprise | 5 TB per seat |

Consumption above the pooled allowance is billed monthly in arrears at USD 0.18
per GB per month, measured as the peak daily usage recorded during that billing
month, not the average.

Accounts that exceed their pooled allowance for three consecutive months are
flagged for a plan review. Storage overage is never discounted, including for
annual and two-year prepay customers.

## 5. Support Response Targets and SLA Credits

Response targets are measured from the moment a ticket is created to the first
substantive human reply. They are targets for first response, not for
resolution.

| Plan | Priority 1 | Priority 2 | Priority 3 |
|---|---|---|---|
| Starter | 1 business day | 2 business days | 3 business days |
| Business | 4 business hours | 1 business day | 2 business days |
| Enterprise | 1 hour, 24x7 | 4 business hours | 1 business day |

Enterprise subscriptions carry a monthly uptime commitment of 99.9 percent.
When measured monthly uptime falls below that commitment, the customer may
claim a service credit calculated as a percentage of that month's subscription
fee:

| Measured monthly uptime | Service credit |
|---|---|
| 99.00 percent to 99.89 percent | 10 percent of the monthly fee |
| 95.00 percent to 98.99 percent | 25 percent of the monthly fee |
| Below 95.00 percent | 50 percent of the monthly fee |

Service credits must be claimed in writing within 30 days of the end of the
affected month. Credits are applied against a future invoice and are never paid
out in cash. The total credit issued in any month is capped at 50 percent of
that month's subscription fee. Starter and Business plans do not carry an
uptime commitment and are not eligible for service credits.

## 6. Onboarding and Professional Services

Professional services are quoted separately from subscription fees and are
invoiced on completion of each milestone.

- Google Workspace migration: USD 1,200 flat rate covering up to 50 mailboxes,
  then USD 18 for each additional mailbox beyond 50.
- Oracle NetSuite implementation: from USD 9,500, scoped per engagement.
- JumpCloud identity and SSO rollout: USD 2,400 flat rate for up to 100 users.
- Administrator training: USD 450 per half-day session, maximum 12 attendees
  per session.
- Out-of-hours cutover surcharge: 30 percent on top of the migration fee where
  the customer requires a weekend or public-holiday cutover window.

Professional services fees are not eligible for the annual or two-year prepay
discount.

## 7. Refunds, Cancellation and Proration

Annual prepay subscriptions on the Starter and Business plans may be cancelled
for a full refund within 14 calendar days of the initial charge, provided the
account has not exceeded 10 percent of its pooled storage allowance.

After the 14-day window, prepaid subscription fees are non-refundable. A
customer who cancels mid-term keeps access until the end of the paid period and
receives no cash refund.

Enterprise subscriptions become non-refundable once onboarding has formally
started, which is defined as the date of the kickoff call recorded in the
project plan.

Professional services and training fees are non-refundable once delivered.
A scheduled training session cancelled with at least 5 business days notice may
be rescheduled once at no charge; later cancellations forfeit the fee.

Refund requests above USD 500, and any refund request relating to an
Enterprise subscription, require approval from a Revenue Operations manager
before processing.

## 8. Currency, Tax and Regional Billing

List prices in this handbook are stated in US dollars. Invoicing is available in
SGD, MYR and IDR at the prevailing monthly reference rate set by Finance on the
first business day of the month.

Applicable indirect tax is added on top of the listed price and is never
included in the figures above:

| Country | Tax | Rate |
|---|---|---|
| Singapore | GST | 9 percent |
| Malaysia | SST | 8 percent |
| Indonesia | PPN | 11 percent |

Customers with a valid tax exemption certificate on file are invoiced without
indirect tax from the start of the next billing cycle after the certificate is
verified.

## 9. Questions This Handbook Does Not Answer

This handbook does not cover technical configuration, data residency,
subprocessor lists, security certifications, or the terms of any individual
negotiated contract. Those questions must be routed to the account team rather
than answered from this document.
