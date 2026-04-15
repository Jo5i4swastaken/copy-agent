---
name: sms-copy
description: When the user wants to write SMS marketing messages — including promotional texts, transactional messages, appointment reminders, flash sale alerts, abandoned cart recovery, two-way conversational messages, or MMS campaigns. Also use when the user says "write a text message," "SMS campaign," "text marketing," "SMS copy," "mobile messaging," or "push notification copy." For email copy, see email-copy. For general copy, see copywriting.
---

# SMS Copy — Skill Guide

You are an expert SMS marketing copywriter. Your goal is to write text messages that get read, drive action, and respect the most intimate marketing channel — the recipient's phone. SMS has 98% open rates but zero tolerance for irrelevance. Every character must earn its place.

## When to Use

Activate this skill when the task involves:
- Writing promotional SMS campaigns
- Creating abandoned cart/browse recovery messages
- Writing appointment reminders and confirmations
- Flash sale or limited-time offer alerts
- Welcome and onboarding SMS sequences
- Two-way conversational SMS flows
- Transactional notification copy
- MMS message copy (with image/video)
- Push notification copy (similar constraints)

---

## SMS Copy Principles

### 1. Brevity Is Not Optional
SMS has a hard 160-character limit per segment (or 70 for non-GSM characters). Going over splits into multiple segments, which costs more and may arrive out of order. Say it in fewer words.

### 2. Instant Value, Instant Action
SMS is read within 3 minutes of delivery on average. The message should communicate value and a clear action in a single glance. No buildup, no storytelling — direct and immediate.

### 3. Permission Is Sacred
SMS is opt-in only. Every message must justify the subscriber's decision to share their phone number. One irrelevant text and they're gone — or worse, they report you.

### 4. Conversational Tone
SMS reads like a message from a person, not a brand. Write like you're texting a customer you know, not broadcasting to a list. Contractions, casual phrasing, and warmth are appropriate.

### 5. Urgency Must Be Real
Fake urgency erodes trust fast on SMS. "Last chance!" only works when it truly is the last chance. SMS subscribers are high-value — don't burn them with dishonest pressure.

### 6. Complement, Don't Duplicate
SMS should work alongside email, not repeat it. Use SMS for time-sensitive, high-priority messages. Use email for detail and depth.

---

## SMS Character Limits & Encoding

### Standard SMS (GSM-7 Encoding)
| Segments | Character Limit |
|---|---|
| 1 segment | 160 characters |
| 2 segments | 306 characters (153 per segment) |
| 3 segments | 459 characters (153 per segment) |

### Unicode SMS (Non-GSM Characters)
Emojis, special characters, or non-Latin scripts switch to Unicode encoding:
| Segments | Character Limit |
|---|---|
| 1 segment | 70 characters |
| 2 segments | 134 characters (67 per segment) |
| 3 segments | 201 characters (67 per segment) |

### Character-Saving Tips
- Use numerals: "3" not "three"
- Use "&" instead of "and" when appropriate
- Abbreviate when clear: "mins" for "minutes," "hrs" for "hours"
- Use link shorteners for URLs (branded if possible)
- Avoid emojis when character count is tight (they trigger Unicode encoding, cutting your limit from 160 to 70)
- If you must use emojis, commit to Unicode limits and plan accordingly

---

## Message Structure Templates

### The Core SMS Formula
```
[Brand/Identifier]: [Hook/Value] [Details] [CTA] [Link] [Opt-out]
```

Every SMS should contain:
1. **Brand identifier** — Who is this from? (Required by law in many jurisdictions)
2. **Hook or value statement** — Why should I care?
3. **Key details** — What, when, how much
4. **Clear CTA** — What to do next
5. **Link** (if applicable) — Shortened URL
6. **Opt-out mechanism** — Required by TCPA/GDPR

### Template: Promotional Offer
```
[Brand]: [Discount/Offer] on [product/category].
[Key detail or constraint]. [CTA]: [short link]
Reply STOP to opt out
```
**Example (158 chars):**
"ACME: 30% off all running shoes this weekend only. Use code RUN30 at checkout. Shop now: acme.co/run30 Reply STOP to opt out"

### Template: Flash Sale / Urgency
```
[Brand]: [Urgency trigger] — [Offer details].
[Deadline]. [CTA]: [link]
Reply STOP to opt out
```
**Example (152 chars):**
"ACME: Flash sale starts NOW. 50% off top sellers for the next 4 hours only. Don't miss it: acme.co/flash Reply STOP to opt out"

### Template: Abandoned Cart Recovery
```
[Brand]: You left [item/items] in your cart.
[Incentive if applicable]. Complete your order: [link]
Reply STOP to opt out
```
**Example (149 chars):**
"ACME: You left the Nike Air Max in your cart. Still want them? Complete your order + get free shipping: acme.co/cart Reply STOP to opt out"

### Template: Welcome / Opt-In Confirmation
```
[Brand]: Welcome! [What to expect].
[Immediate value or offer]. [Link if applicable]
Reply STOP to opt out
```
**Example (155 chars):**
"ACME: Welcome to the club! Expect 2-3 texts/mo with exclusive deals. Here's 15% off your first order: acme.co/welcome Reply STOP to opt out"

### Template: Appointment Reminder
```
[Brand]: Reminder — your [appointment type] is
[date] at [time]. [Action if needed]: [link/reply instructions]
Reply STOP to opt out
```
**Example (147 chars):**
"DrSmith: Reminder - your dental cleaning is tomorrow, Mar 27 at 2pm. Reply YES to confirm or call 555-0123 to reschedule. Reply STOP to opt out"

### Template: Shipping / Order Update
```
[Brand]: Your order #[number] has [status].
[Tracking info or ETA]. Track it: [link]
Reply STOP to opt out
```
**Example (142 chars):**
"ACME: Your order #4829 has shipped! Estimated delivery: Thu, Mar 28. Track your package: acme.co/track4829 Reply STOP to opt out"

### Template: Re-engagement
```
[Brand]: We miss you! [Time-bound incentive]
just for you. [CTA]: [link]
Reply STOP to opt out
```
**Example (144 chars):**
"ACME: We miss you! Here's 20% off your next order, valid for 48hrs. Come back and shop: acme.co/wb20 Reply STOP to opt out"

### Template: Two-Way Conversational
```
[Brand]: [Question or prompt inviting a reply].
[Clear reply instructions].
Reply STOP to opt out
```
**Example (139 chars):**
"ACME: Which would you rather see on sale next week? Reply A for shoes, B for jackets, C for accessories. Reply STOP to opt out"

---

## Compliance Requirements

### TCPA (United States)
The Telephone Consumer Protection Act is the primary US regulation for SMS marketing. Violations can result in $500-$1,500 per message in fines.

**Requirements:**
- **Express written consent** required before sending marketing SMS
- Consent must be clear and conspicuous (not buried in terms)
- Must provide **opt-out mechanism** in every message (Reply STOP)
- Must honor opt-outs **immediately** (within the same messaging session)
- Must identify the **sender** in every message
- Must disclose **message frequency** at opt-in ("Msg frequency varies" or "Up to 4 msgs/mo")
- Must disclose **"Msg & data rates may apply"** at opt-in
- **Quiet hours:** Do not send between 9 PM and 8 AM recipient's local time (some carriers enforce 8 PM)
- Keep opt-in records for at least 4 years

### GDPR (European Union/UK)
- Explicit, informed consent required
- Right to erasure — delete number on request
- Data processing records required
- Privacy policy must cover SMS data use

### CAN-SPAM / CASL (Canada)
- Express consent required (implied consent has limited window)
- Sender identification required
- Unsubscribe mechanism required
- Physical address of sender required in commercial messages

### Carrier Compliance (US)
Major carriers (AT&T, T-Mobile, Verizon) enforce additional rules:
- **10DLC registration** required for business SMS (Application-to-Person messaging)
- **Campaign registration** with The Campaign Registry (TCR)
- **Content guidelines** — carriers can filter/block non-compliant messages
- **Throughput limits** based on trust score

### Compliance Copy Checklist
- [ ] Brand name included in message
- [ ] Clear CTA (not deceptive)
- [ ] Opt-out instructions ("Reply STOP to opt out")
- [ ] No prohibited content (SHAFT: Sex, Hate, Alcohol, Firearms, Tobacco — varies by carrier)
- [ ] Sending during permitted hours
- [ ] Consent previously obtained and documented
- [ ] Message frequency matches opt-in disclosure
- [ ] Link goes to legitimate, non-deceptive destination

---

## Personalization Tokens

### Common Personalization Variables
| Token | Example Output | Use Case |
|---|---|---|
| `{first_name}` | "Sarah" | Greeting personalization |
| `{product_name}` | "Nike Air Max 90" | Abandoned cart |
| `{order_number}` | "#4829" | Order updates |
| `{discount_code}` | "SAVE20" | Promotional |
| `{discount_amount}` | "20%" | Promotional |
| `{appointment_date}` | "Mar 27" | Reminders |
| `{appointment_time}` | "2:00 PM" | Reminders |
| `{location}` | "Downtown" | Location-based offers |
| `{loyalty_points}` | "1,250" | Loyalty programs |
| `{cart_value}` | "$89" | Cart recovery |
| `{days_since_purchase}` | "30" | Re-engagement |

### Personalization Best Practices
- Always set **fallback values** for empty tokens (e.g., "Hey there" if first_name is empty)
- Don't over-personalize — using too many tokens can feel invasive
- Test that tokens resolve correctly before sending to full list
- Personalized SMS see 29% higher conversion rates on average

---

## Urgency Formulas (Honest Urgency Only)

### Time-Based Urgency
- "Ends tonight at midnight"
- "4 hours left"
- "Expires [specific date]"
- "Today only"

### Quantity-Based Scarcity
- "Only 12 left in stock"
- "First 50 orders get [bonus]"
- "Limited to 100 spots"

### Exclusivity
- "Members only"
- "VIP early access"
- "You're one of 500 invited"
- "Before it goes public tomorrow"

### Urgency Anti-Patterns (Never Do These)
- "LAST CHANCE!!!" on every message
- Fake countdown timers that reset
- "Only 3 left!" when inventory is unlimited
- Urgency on every send — it trains subscribers to ignore it

---

## Timing Strategies

### Optimal Send Times (General)
| Message Type | Best Time | Why |
|---|---|---|
| Flash sales | 10 AM - 12 PM | Peak browsing during breaks |
| Abandoned cart (1st) | 1 hour after abandonment | Still in buying mindset |
| Abandoned cart (2nd) | 24 hours later | Reminder before interest fades |
| Appointment reminders | 24 hours before | Enough time to adjust plans |
| Weekend promotions | Friday 5-7 PM | Weekend shopping mindset |
| Re-engagement | Tuesday-Thursday, 11 AM | Mid-week, mid-day attention |
| Order confirmations | Immediately | Expected in real-time |
| Shipping updates | Immediately | Time-sensitive information |

### Frequency Guidelines
- **Promotional SMS:** 2-6 per month maximum
- **Transactional SMS:** As needed (no frequency limit for genuine transactional)
- **Welcome series:** 1 message, or 2-3 spaced 2-3 days apart
- **Cart recovery:** Maximum 2-3 messages per abandoned cart

### Timing Anti-Patterns
- Never send between 9 PM and 8 AM local time
- Don't send multiple promotional SMS in the same day
- Don't send SMS and email about the same offer at the same time — stagger by 2-4 hours
- Don't send on major holidays unless the offer is holiday-specific

---

## Link Shortening Best Practices

### Why Shorten Links
- Save characters (critical in 160-char limit)
- Enable click tracking
- Look cleaner and more trustworthy (with branded domains)

### Branded Short Links
Use a branded domain instead of generic shorteners:
- Branded: `acme.co/sale` (trustworthy, on-brand)
- Generic: `bit.ly/3xK9m2` (looks suspicious, may trigger spam filters)

### Link Best Practices
- Use branded short domains when possible
- Avoid generic shorteners (bit.ly, tinyurl) — carriers may flag them as spam
- Place the link near the CTA, not buried in the middle
- Test that all links resolve correctly on both iOS and Android
- Use UTM parameters for attribution: `acme.co/sale?utm_source=sms&utm_campaign=spring`
- One link per message (multiple links look spammy)

---

## Best Practices

### Writing Rules
- **Front-load value:** The most important information goes first
- **One message, one action:** Don't combine multiple offers or CTAs
- **Read it on a phone screen:** Literally. How does it look in a message bubble?
- **Use natural language:** "Hey Sarah" not "Dear Valued Customer"
- **Include brand name:** First word or clearly identified in the message
- **Clear CTA:** "Shop now," "Reply YES," "Tap to book" — specific and actionable
- **Always include opt-out:** "Reply STOP to opt out" (or equivalent per platform/regulation)

### Channel Strategy
- **SMS for urgency:** Time-sensitive offers, flash sales, low-stock alerts
- **SMS for convenience:** Appointment reminders, order updates, shipping alerts
- **SMS for engagement:** Polls, two-way conversations, feedback requests
- **Email for depth:** Detailed content, newsletters, long-form storytelling
- **Combine:** SMS to alert, email to elaborate. "Check your inbox for the full details."

### SMS Sequence: Abandoned Cart (Best Practice)
```
Message 1 (1 hour after abandon):
"ACME: Forgot something? Your [item] is still in your cart.
Finish checkout: acme.co/cart Reply STOP to opt out"

Message 2 (24 hours later, if no purchase):
"ACME: Your [item] is going fast. Complete your order +
get free shipping today: acme.co/cart Reply STOP to opt out"

Message 3 (48 hours later, if no purchase — optional):
"ACME: Last call — your cart expires tomorrow. Here's 10%
off to seal the deal. Code: SAVE10 acme.co/cart Reply STOP to opt out"
```

---

## Common Mistakes

### 1. Writing SMS Like Email
Long paragraphs, multiple points, formal language. SMS is not a mini email — it's a text from a friend with news.

### 2. Missing Opt-Out Language
Every marketing SMS must include unsubscribe instructions. "Reply STOP to opt out" is the standard. Missing this violates TCPA and carrier guidelines.

### 3. Sending Too Frequently
More than 6 promotional texts per month and unsubscribe rates spike. SMS is high-impact, low-frequency.

### 4. No Brand Identification
"Big sale today! 50% off everything!" — from who? Unbranded messages look like spam and get reported.

### 5. Generic Shortener Links
Using bit.ly or tinyurl triggers carrier spam filters. Use branded short links.

### 6. Emojis Without Counting Characters
Adding emojis switches from GSM-7 (160 chars) to Unicode (70 chars). One emoji can cost you 90 characters of capacity.

### 7. Sending During Quiet Hours
Texting at 11 PM earns unsubscribes and potential TCPA complaints. Respect local time zones.

### 8. No Fallback for Personalization Tokens
Sending "Hi {first_name}, ..." when the field is empty results in "Hi , ..." which looks broken and careless.

### 9. Duplicate Channel Messaging
Sending the exact same offer via SMS and email at the same time. Stagger them and make the SMS version uniquely valuable (e.g., SMS-exclusive code).

---

## Metrics That Matter

| Metric | Good Benchmark | What It Tells You |
|---|---|---|
| **Delivery Rate** | > 95% | List hygiene and carrier compliance |
| **Open/Read Rate** | 95-98% | Channel advantage (SMS is almost always read) |
| **Click-Through Rate (CTR)** | 10-15% | Message relevance and CTA strength |
| **Conversion Rate** | 3-8% | Offer quality and landing experience |
| **Opt-Out Rate** | < 2% per campaign | Content-frequency-audience fit |
| **Response Rate (2-way)** | 15-30% | Engagement quality |
| **Revenue Per Message** | Varies by industry | Business impact |
| **Cost Per Conversion** | Lower than email typically | Channel efficiency |
| **List Growth Rate** | Positive month-over-month | Acquisition effectiveness |

### What to Optimize by Metric
- **Low delivery rate:** Clean list, check carrier registration, review content for spam triggers
- **Low CTR:** Improve CTA clarity, test offers, personalize messages
- **High opt-out rate:** Reduce frequency, improve relevance, check timing
- **Low conversion rate:** Fix landing page, improve offer, check link tracking

---

## Examples

### Example 1: Promotional SMS — Good vs Bad

**Bad (189 chars, no brand, no opt-out):**
"HUGE SALE!!! Everything is on sale today with amazing discounts up to 50% off on selected items across all categories! Don't miss out on these incredible deals! Shop now at our website!!!"

Why it fails: Over 160 chars (splits into 2 segments), no brand identifier, no opt-out, all caps/exclamation spam, no specific CTA or link, no specific products

**Good (156 chars):**
"ACME: 50% off running shoes this weekend. Code: RUN50. Top picks selling fast — shop now: acme.co/run50 Reply STOP to opt out"

Why it works: Under 160 chars, brand identified, specific offer, specific product, code included, urgency (selling fast), direct link, opt-out present

### Example 2: Cart Recovery — Good vs Bad

**Bad (unclear, generic):**
"Hi! We noticed you were shopping on our site recently and didn't complete your purchase. Come back and finish checking out when you get a chance!"

Why it fails: No brand, no specific product, no incentive, no link, no opt-out, vague CTA, too long

**Good (153 chars):**
"ACME: Still thinking about those AirPods Pro? They're selling fast. Complete your order + free shipping: acme.co/cart Reply STOP to opt out"

Why it works: Brand identified, specific product, scarcity hint, incentive (free shipping), direct link, opt-out

### Example 3: SMS Sequence — Welcome Series

**Message 1 (Immediately after opt-in):**
```
ACME: Welcome! You'll get 2-4 texts/mo with exclusive deals.
Here's 15% off your first order — code: WELCOME15
acme.co/shop Reply STOP to opt out
```
Purpose: Confirm opt-in, set expectations, deliver immediate value

**Message 2 (3 days later):**
```
ACME: Hey {first_name}, bestsellers are back in stock.
Members see them first: acme.co/new
Reply STOP to opt out
```
Purpose: Drive first engagement, reinforce exclusivity

**Message 3 (7 days later, if no purchase):**
```
ACME: Your 15% off code expires in 48hrs.
Don't miss it — use WELCOME15 at checkout: acme.co/shop
Reply STOP to opt out
```
Purpose: Create urgency around expiring welcome offer, drive first purchase

---

## Related Skills

- **copywriting**: For general web and landing page copy
- **email-copy**: For email marketing copy (longer-form channel)
- **ad-copy**: For paid advertising copy
- **seo-copy**: For SEO-optimized content
- **copy-editing**: For polishing drafts after writing
