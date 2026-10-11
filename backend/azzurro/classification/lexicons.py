"""Topic keyword lexicons (lowercase; multi-word phrases supported).

Polarity is NOT decided by these words - Booking.com already splits each
review into a "Liked" and "Disliked" section, so a keyword hit inside the
negative section counts as a negative mention and vice versa. The lexicons
only decide WHICH operational topic a sentence is about.
"""
from __future__ import annotations

TOPICS: dict[str, list[str]] = {
    "cleanliness": [
        "clean", "unclean", "dirty", "dirt", "filthy", "filth", "grimy",
        "grime", "stained", "stains", "mould", "mold", "mouldy", "moldy",
        "smell", "smelled", "smelt", "smelly", "stink", "stunk", "stinky",
        "odour", "odor", "housekeeping", "uncleaned", "tidy", "untidy",
        "hair in", "bed bugs", "bedbugs", "cockroach", "cockroaches",
        "roach", "roaches", "ants", "insects", "bugs in", "dusty", "dust",
        "garbage", "rubbish", "trash", "washed", "unwashed", "sanitised",
        "sanitized", "hygiene", "fingerprints", "toothpaste", "bathroom was dirty",
    ],
    "check-in": [
        "check in", "check-in", "checking in", "checkin", "checked in",
        "check out", "check-out", "checkout", "checked out", "early check",
        "late check", "key collection", "collect the key", "keys", "key box",
        "lockbox", "lock box", "self check", "arrival", "arriving",
        "reception was closed", "front desk", "waiting to check", "luggage",
        "baggage storage", "left our bags", "express check",
    ],
    "staff": [
        "staff", "receptionist", "reception", "concierge", "manager",
        "housekeeper", "cleaner", "cleaners", "porter", "front office",
        "host", "unfriendly", "rude", "helpful", "unhelpful", "polite",
        "welcoming", "service", "customer service", "attitude", "ignoring",
        "ignored", "accommodating", "obliging", "courteous", "dismissive",
        "hostel staff", "night manager", "duty manager",
    ],
    "noise": [
        "noise", "noisy", "loud", "loudly", "sound", "sounds", "party",
        "parties", "partying", "banging", "banged", "slamming", "slammed",
        "music", "screaming", "screamed", "shouting", "shouted", "yelling",
        "barking", "traffic noise", "street noise", "thin walls",
        "paper thin walls", "could hear", "kept us awake", "woken", "woke us",
        "earplugs", "snoring", "karaoke", "bar downstairs", "pub next",
        "construction", "renovation", "drills", "sirens", "revellers",
        "revelers", "club", "nightclub",
    ],
    "facilities": [
        "facilities", "facility", "amenities", "wifi", "wi-fi", "internet",
        "air conditioning", "aircon", "air con", "a/c", "heating", "heater",
        "lift", "elevator", "staircase", "stairs", "kitchen", "kitchenette",
        "common room", "shared bathroom", "shared toilet", "shared shower",
        "bathroom", "shower", "toilet", "laundry", "washing machine",
        "dryer", "breakfast", "parking", "gym", "pool", "towel", "towels",
        "fridge", "refrigerator", "microwave", "tv", "television", "fan",
        "powerpoint", "power point", "socket", "outlet", "locker", "lockers",
        "storage", "luggage room", "vending", "hot water", "water pressure",
    ],
"location": [
        "location", "located", "position", "situated", "area", "neighbourhood",
        "neighborhood", "suburb", "walk to", "walking distance", "close to",
        "near the", "far from", "transport", "train station",
        "bus stop", "metro", "tram", "airport", "central", "cbd",
        "city centre", "downtown", "waterfront", "harbour", "harbor",
        "shops", "restaurants", "cafes", "safe area", "convenient",
        "quiet street",
    ],
    "room-condition": [
        "room", "rooms", "bed", "beds", "bedding", "mattress", "pillow",
        "pillows", "blanket", "blankets", "duvet", "sheets", "linen",
        "cramped", "tiny room", "small room", "cramped", "cluttered",
        "broken", "damaged", "cracked", "leaking", "leak", "damp", "dark room",
        "window", "windows", "no window", "view", "carpet", "wardrobe",
        "closet", "furniture", "outdated", "dated", "run down", "rundown",
        "shabby", "worn", "wobbly", "squeaky", "paint", "wallpaper",
        "ceiling", "floorboards", "hooks", "blind", "blinds", "curtains",
    ],
    "value": [
        "value", "worth", "price", "priced", "pricing", "expensive",
        "overpriced", "cheap", "cheaper", "cost", "costed", "money",
        "rip off", "ripoff", "budget", "affordable", "pay for", "paid",
        "value for money", "not worth", "bang for buck", "hidden fee",
        "extra charge", "surcharge", "deposit", "refund",
    ],
}

# Words that invert sentiment within a clause ("not clean" in the positive
# section is rare, but cheap to guard against).
NEGATIONS = ["not", "no", "never", "hardly", "isn't", "wasn't", "aren't",
             "weren't", "don't", "didn't", "doesn't", "nothing"]
