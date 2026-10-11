# Quick Start — get the dashboard running

You need a computer with **Python 3.12+**, **Node.js 20+ (22 recommended)** and **Google Chrome**
installed. No accounts or passwords. The guest reviews are already included
in the download, so the dashboard works straight away without visiting
Booking.com.

---

## Step 1 — Install the building blocks (one time only)

Open a terminal in this folder and paste:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

This takes a minute or two. It only puts files inside this folder —
nothing on your computer is changed.

## Step 2 — (Optional) Build the dashboard screen

The download already contains a ready-built dashboard, so you can skip this
step. Only needed after someone changes the design:

```bash
cd frontend && npm install && npm run build && cd ..
```

## Step 3 — Start it

```bash
make demo
```

Then open this address in your browser:

**http://127.0.0.1:8000**

That's it — you should see the "Azzurro Hotels · Guest Review Dashboard" with
hundreds of real guest reviews already loaded. Leave the terminal window open
while you use it; press `Ctrl + C` in the terminal to stop.

---

## Getting fresh reviews later

When you want the latest reviews from Booking.com (e.g. once a day or once a
week), run:

```bash
make update
```

You'll see a progress line for each hotel, like:

```
[1/4] Olympic Hotel Paddington: 0 new, 10 checked in 12s — up to date
```

It finishes in about 1–2 minutes, then run `make demo` again to view.

Stuck or something looks wrong? See [USER_GUIDE.md](USER_GUIDE.md) for what
the screen means, or [README.md](README.md) for the technical detail.
