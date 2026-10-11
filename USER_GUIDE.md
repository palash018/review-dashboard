# User Guide — Guest Review Dashboard

A guide for operations staff. No technical knowledge needed.

The dashboard shows what guests say about our four properties on Booking.com:
**Olympic Hotel Paddington, Potts Point, Central Sydney and Darling Harbour**.

---

## What you see on screen

### Top bar
- **Property buttons** — tap one to look at just that hotel, or "All" for
  everything together.
- **Period buttons** — how far back to look: this week, last week, the last
  4 or 12 weeks, all time, or your own date range.
- **Time zone** — the clock in the top right. It's set to Sydney time by
  default. This changes only how times and week boundaries are shown; it
  never changes the reviews themselves.
- **"Latest data"** — when reviews were last collected from Booking.com.

### The four number cards
Each card compares **the period you picked** with the similar period before
it (for "This week", that's last week):
- **Average score** — the guests' average rating out of 10. The small green
  or red line tells you if it went up or down.
- **Reviews received** — how many guests left reviews.
- **Negative share** — what portion of reviews were unhappy ones.
- **Guest sentiment mix** — the green/grey/red bar showing happy, middle, and
  unhappy reviews.

Green means improving, red means getting worse. "No data for comparison"
simply means we have no reviews from the earlier period.

### "What guests complained about"
The most common problems guests wrote about, in plain English — for example:
*"Cleanliness — 40% of complaint reviews mentioned this (+15pp)"* means 40%
of reviews with complaints mentioned cleaning, and that's 15 points worse
than the previous period. **Tap any complaint line** and the page jumps down
to the actual guest reviews behind the number.

### Property breakdown
One row per hotel: its average score, whether it went up or down, and its
**top issue**. Tap "Top issue: …" to see those exact reviews.

### Charts
- **Average rating per week** — the score line over time.
- **Positive / neutral / negative reviews** — how many of each kind arrived
  each week.

### Review feed
Every guest review, newest first. Each card shows the hotel, the rating, the
date, what the guest liked and disliked, and coloured topic tags. Use the
boxes at the top to narrow the list: search for a word, pick a topic (e.g.
Noise), or show only negative reviews. Sort by "Lowest rated" to see the
worst experiences first.

---

## Common questions

**A tag says "Location" but I searched for "location" and found nothing.**
Topic tags match *phrases* guests actually wrote, like "far from the city" —
not the word "location" itself. Use the **topic dropdown** in the review
feed, or tap the tag/issue line anywhere on the page. To see *why* a review
was tagged, hover over the tag with your mouse (on a computer): it shows the
exact words that triggered it, e.g. *"Tagged because the review mentions:
dirty, mould"*.

**It's Monday and the numbers are empty.**
A new week starts with zero reviews. Instead of showing you a blank page,
the dashboard automatically shows last week and displays a yellow notice.
Press "Show current week anyway" if you really want the empty week.

**The average went down — where do I start looking?**
1. Check the complaint list — a red "worsening" tag shows what got worse.
2. Check Property breakdown — see which hotel dropped.
3. Tap that hotel's top issue to read the actual guest comments.

**Are the topic tags always right?**
They're produced automatically by matching common words and phrases, so
they're very good at spotting clear complaints but can occasionally miss an
unusual phrase or tag something debatably. Always read the actual review
before acting on it. The tag tooltip (hover on a computer) shows exactly
which words were matched, so you can judge for yourself. An optional
AI-assisted mode exists — ask whoever looks after the system; the label in
the top bar says which mode is active: "Keyword-based tags" or
"AI-assisted tags".

**The reviews seem outdated.**
Someone needs to run the refresh (`make update`) — see
[QUICKSTART.md](QUICKSTART.md), or ask whoever set the system up. The
"Latest data" time in the top bar tells you how fresh the data is.

**Does it work on my phone?**
Yes. On a small screen the property and period buttons become swipeable
strips, and everything stacks so nothing is cut off.

---

## Quick reference

| What you want | What to do |
|---|---|
| One hotel only | Tap its name in the top bar |
| Last month | Tap "Last 4 weeks" |
| The worst reviews first | Review feed → sort → "Lowest rated" |
| All noise complaints | Review feed → topic → "Noise" |
| Reviews mentioning "cockroaches" | Type it in the search box |
| Why was this tagged "Cleanliness"? | Hover / tap-and-hold the tag |
| What got worse this week? | Look for red "worsening" tags in the complaints list |
| Yesterday's new reviews | Period → "This week", sort → "Newest first" |
