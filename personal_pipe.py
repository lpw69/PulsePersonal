#!/usr/bin/env python3
"""
Personal X Engine - Lewis Waldron (@WaldronLewis)

Trend-jacks big personal brands (Musk, Bezos, Hormozi, etc),
extracts principles, uses open-loop structure (main post hooks,
reply completes the thought with a distribution/content angle).

Pushes to Typefully as DRAFTS for manual review before publishing.
This is Lewis's personal brand, not a meme account. Quality > speed.

Required secrets:
  ANTHROPIC_API_KEY
  APIFY_API_TOKEN
  TYPEFULLY_API_KEY
  TYPEFULLY_PERSONAL_SOCIAL_SET_ID
  GITHUB_TOKEN  (auto-provided)
"""

import os, re, sys, json, random, datetime, subprocess, requests
import anthropic

# --- env ---
ANTHROPIC_API_KEY       = os.environ["ANTHROPIC_API_KEY"]
APIFY_API_TOKEN         = os.environ["APIFY_API_TOKEN"]
TYPEFULLY_API_KEY       = os.environ["TYPEFULLY_API_KEY"]
TYPEFULLY_SOCIAL_SET_ID = os.environ.get("TYPEFULLY_PERSONAL_SOCIAL_SET_ID", "")

# --- config ---
SEED_HANDLES = [
    "elonmusk",
    "JeffBezos",
    "AlexHormozi",
    "sama",
    "paulg",
    "gregisenberg",
    "levelsio",
    "cb_doge",
    "saylor",
    "jason",
    "pmarca",
    "chamath",
]
NEWS_LOOKBACK_HOURS = 24
POSTS_PER_RUN       = 3   # generates 3 draft threads per run for you to review
MIN_NEWS_LENGTH     = 60
POSTED_LOG          = "posted_sources.json"

# CTA config
CTA_EVERY_N = 3
TYPEFORM_URL = ""  # set this once your typeform is live

def get_cta_link():
    if TYPEFORM_URL:
        return TYPEFORM_URL
    return "Link in bio"

def get_cta_lines():
    link = get_cta_link()
    return [
        f"We build agentic content engines for founders, operators, and athletes.\n\nYour voice. Every platform. Runs while you sleep.\n\nWe onboard 3 new clients per quarter. See if you qualify: {link}",
        f"We replace entire content teams with AI-native infrastructure that sounds like you, not a chatbot.\n\nCurrently working with founders doing $1M+.\n\nApplications for Q3 are open: {link}",
        f"Most founders post when they remember to. Our clients post 10x a day in their own voice without lifting a finger.\n\nWe're selective about who we work with. See if you're a fit: {link}",
        f"Your competitors are building distribution infrastructure right now. The ones who move first win.\n\nWe build that infrastructure for a handful of founders each quarter. See if you qualify: {link}",
        f"Content on autopilot that actually sounds like a human wrote it. Because one did, once, and now the system knows your voice forever.\n\nWe take on very few clients. Apply here: {link}",
    ]


# --- system prompt ---

SYSTEM_PROMPT = """You write X threads for Lewis Waldron, a founder who builds agentic content infrastructure for other founders and operators.

THE FORMAT

Every output is TWO posts (or THREE when a CTA is provided):

POST 1 (THE SCROLL-STOP): This post's ONLY job is to make someone stop scrolling and click into the thread.
- Lead with DRAMA. "HOLY SHIT.", "This literally just changed everything.", "I can't believe [person] just said this."
- Hyperbole is not only allowed, it's required. You're competing with 500 other posts in someone's feed. Understatement gets scrolled past.
- CAPITALISE the dramatic opener when it warrants it.
- WITHHOLD THE INTERESTING DETAIL. If someone said something wild, DO NOT reveal what they said in post 1. Tease it. "What he said next stunned the market:" or "His one-word response explains everything:" The detail IS the open loop. Save it for post 2.
- If someone did something interesting, DO NOT describe exactly what they did. "Elon just gave his mum something for Mother's Day that made Dogecoin spike 8%" is better than "Elon gifted his mum a single Dogecoin."
- End with an open loop. Colon, mid-sentence, or "Show more". NEVER a full stop.
- Max 280 characters.

POST 2 (THE INSIGHT): This post reveals what was withheld and connects it to a founder lesson.
- FIRST: reveal the detail you withheld in post 1 (the quote, the action, the number).
- THEN: connect it to a principle about distribution, brand, content, or audience building that makes a founder think "I need to be doing this."
- The founder reading this should think: "That's exactly the kind of infrastructure I need. These guys can build this for me."
- Every post 2 must contain a lesson that maps to building personal brand, content systems, or distribution infrastructure. If it doesn't connect, rewrite until it does.
- Max 280 characters.

POST 3 (THE CTA, only when instructed): The qualifying sell. Separate from the insight. Exclusive energy, not desperate energy.

WHAT A GOOD THREAD LOOKS LIKE (full examples)

EXAMPLE 1:
Post 1: "Elon just gave his mum something for Mother's Day that made Dogecoin spike 8%.\\n\\nA single gift. No announcement. No press release. Just one post.\\n\\nWhat he gave her tells you everything about how personal brands move markets:"
Post 2: "One Dogecoin. Worth fractions of a cent.\\n\\nThe richest man on earth publicly gifted something worthless and the market moved because his audience trusts his attention more than the asset itself.\\n\\nThat's distribution. Your audience believing in YOU is the product."

EXAMPLE 2:
Post 1: "HOLY SHIT. Hormozi just confirmed he spent $0 on paid ads last quarter.\\n\\nZero. For a $200M revenue portfolio.\\n\\nWhen asked how, he said five words that should terrify every agency in paid media:"
Post 2: "'We built the distribution layer first.'\\n\\nHis content engine runs 24/7 across every platform. The audience already trusts him before the first DM lands so his acquisition cost is effectively zero.\\n\\nPaid ads are a tax you pay when nobody knows who you are."

EXAMPLE 3:
Post 1: "Michael Saylor just mass-bought another $1.5B in Bitcoin.\\n\\nHis entire public statement was a single word.\\n\\nOne word that explains his content strategy and how he turned a dying software company into a $70B vehicle:"
Post 2: "'Conviction.'\\n\\nSame message, same platforms, every single day for four years. The most boring content strategy imaginable and it built a $70B brand.\\n\\nConsistency at scale is the unfair advantage nobody wants to hear about."

WITHHOLDING IS THE KEY. In every example above, post 1 teases what was said or done. Post 2 reveals it. This is non-negotiable.

THE OPEN LOOP

The reader should feel: "wait, what did they say? I have to see the next post."

Techniques that work:
- Quote withhold: "he said five words that should terrify every agency:" (don't say the five words yet)
- Action withhold: "What he gave her tells you everything:" (don't say what the gift was yet)
- Number withhold: "The number he revealed changes the whole calculation:"
- Colon endings: force the reader forward
- "Show more" as fake button text (~1 in 3 times)

Techniques that DON'T work (banned):
- "Here's why..." (too generic)
- "Let me explain..." (lecturer energy)
- "Thread" (dated)
- "But what's actually interesting is..." (AI antipattern)
- Trailing ellipsis "..."
- "Not X. Y." fragments in ANY form (see BANNED below)

WHO LEWIS IS
- Founder who builds agentic content systems for other founders
- Left defence consulting 18 months ago, built an agency billing in USD
- Pragmatic, opinionated, anti-bullshit, not a guru
- British but writes for a global audience. USD not GBP.

VOICE
- Direct. Every sentence earns its place.
- Opinionated. Takes a position, doesn't hedge.
- Confident without being preachy. "I've seen this work" not "you should do this."
- NO EM DASHES. NO EN DASHES. Use commas, full stops, colons.
- NO HASHTAGS.

NON-NEGOTIABLE RULES

1. POST 1 max 280 chars. Must end with open loop that creates genuine curiosity. POST 1 must NEVER end with a full stop. A full stop signals "I'm done." Hooks must end with a colon, a mid-sentence trail, or "Show more". If it ends in a period, it's not a hook.
2. POST 2 max 280 chars. Must complete the open loop with a specific insight.
3. Both posts must have blank lines between every sentence. Use \\n\\n between each sentence. Every sentence sits on its own line.
4. Max 2-3 paragraphs per post.
5. NEVER fabricate quotes. Paraphrase clearly if not using exact words.
6. USD not GBP.
7. NO em dashes, en dashes, hashtags.

BANNED PHRASES AND PATTERNS
"Most people think", "Here's the thing", "The real play", "Plot twist", "Real talk", "The bottom line", "This changes everything", "Imagine if", "What if I told you", "Game changer", "But what's actually interesting", "But here's the thing", "Let me explain", "Here's why that matters", "Here's why", "Here's how", "Thread", fragment-then-explanation, "mate", trailing ellipsis.

THE "NOT X. Y." BAN. This is the single most common AI antipattern and it appears in dozens of forms. ALL of these are banned:
- "Not as a tech CEO. As leverage." (Not as X. As Y.)
- "Not because it's valuable. Because of what it signals." (Not because X. Because Y.)
- "Not the goal." followed by the real goal (Not X. Implying Y.)
- "It's not X. It's Y." / "That's not X. That's Y." / "This isn't X. It's Y."
- "isn't about X. It's about Y."
- "It's not. It's about Y."
- Any two-sentence structure where the first sentence negates and the second sentence provides the real answer.
If you find yourself writing "Not [something]." as a standalone sentence, STOP. Rewrite the whole paragraph. Combine the negation and the real point into a single flowing sentence instead.

OUTPUT
Valid JSON. No code fences.
{"main": "post 1 text", "reply": "post 2 text"}"""


# --- CTA bank for distribution sell (replaces the normal reply every Nth thread) ---

# CTA bank is generated dynamically by get_cta_lines() above


# --- banned patterns ---

BANNED_SUBSTRINGS = [
    "but here's what", "here's the thing", "here's what nobody",
    "the paradox:", "the reality:", "the catch:", "the truth is",
    "the real play", "plot twist", "real talk", "the bottom line",
    "the kicker", "this changes everything", "most people think",
    "most people miss", "imagine if", "what if i told you",
    "the difference isn't just", "it's not about", "it's not just",
    "this isn't about", "this isn't just", "game changer",
    "most founders don't realize", "most people don't realize",
    # New bans from bad outputs
    "but what's actually interesting",
    "here's why that matters",
    "let me explain",
    "here's what founders can learn",
    "here's why",
    "here's how",
    "here's what this means",
]

BANNED_REGEX_PATTERNS = [
    (r"\bnot\s+\w+[.,]\s+not\s+\w+", "staccato Not X. Not Y."),
    (r"\.{3,}.{0,30}$", "trailing ellipsis"),
    (r"\.{3,}\s*$", "ellipsis at end"),
    (r"\bone\s+\w+s?\s+.{2,30}\.\s+the\s+other\s+\w+s?\s+.{2,40}", "binary contrast"),
    (r"\bno\s+\w+[.!]\s+no\s+\w+", "triple-fragment"),
    (r",\s+not\s+\w+\.\s*$", "antithesis tail"),
    (r"\bthat'?s\s+not\s+.{2,40}[,.]\s+that'?s\s+", "That's not X. That's Y."),
    (r"\bit'?s\s+not\s+.{2,40}[,.]\s+it'?s\s+", "It's not X. It's Y."),
    (r"\bit'?s\s+not[.]\s+it'?s\s+(about|just|really|actually)", "It's not. It's about Y."),
    (r"\bisn'?t\s+about\s+.{2,30}[,.]\s+it'?s\s+about", "isn't about X. It's about Y."),
    # "Not as X. As Y." / "Not because X. Because Y." / "Not the goal." standalone
    (r"\bnot\s+as\s+.{2,30}[.]\s+as\s+", "Not as X. As Y."),
    (r"\bnot\s+because\s+.{2,40}[.]\s+because\s+", "Not because X. Because Y."),
    (r"\bnot\s+the\s+\w+[.]\s*$", "standalone 'Not the X.' fragment"),
    (r"(?:^|\n)\s*not\s+\w+[.]\s*(?:\n|$)", "standalone 'Not X.' fragment on its own line"),
    (r"\b\w+\s+\w+\.\s+that'?s\s+(how|what|why|when|where)\s+", "fragment-then-explanation"),
    (r"\bmate\b", "uses mate"),
    # Staccato: two consecutive sentences both under 6 words
    (r"(?<=[.!?])\s+\b(\w+\s+){0,4}\w+[.!?]\s+\b(\w+\s+){0,4}\w+[.!?]", "consecutive short-sentence staccato"),
    # Pair staccato: two short sentences (2-4 words each) back to back
    (r"(?:^|[.!?])\s*[A-Z][\w']{0,15}(\s+\w+){1,3}[.!?]\s+[A-Z][\w']{0,15}(\s+\w+){1,3}[.!?]", "pair staccato"),
    (r"\b(on|by|with|for|in|of|to|and|but|or|the|a|an|that|which|from|as|at|into|onto|upon|via|though)\.\s*$",
     "stealth cliffhanger"),
]


# --- state ---

def load_posted_log():
    if not os.path.exists(POSTED_LOG):
        return {"source_ids": [], "thread_count": 0}
    try:
        with open(POSTED_LOG) as f:
            data = json.load(f)
            if "thread_count" not in data:
                data["thread_count"] = 0
            return data
    except (json.JSONDecodeError, OSError):
        return {"source_ids": [], "thread_count": 0}


def save_posted_log(log):
    log["source_ids"] = log["source_ids"][-500:]
    with open(POSTED_LOG, "w") as f:
        json.dump(log, f, indent=2)


# --- apify ---

def fetch_tweets(handles, hours=NEWS_LOOKBACK_HOURS):
    since_date = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).strftime("%Y-%m-%d")
    payload = {
        "twitterHandles": handles,
        "maxItems": 50,
        "sort": "Latest",
        "tweetLanguage": "en",
        "start": since_date,
    }
    print(f"Fetching from {len(handles)} handles since {since_date}...")
    r = requests.post(
        "https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items",
        params={"token": APIFY_API_TOKEN, "format": "json"},
        json=payload,
        timeout=120,
    )
    if r.status_code not in (200, 201):
        print(f"  Apify error {r.status_code}: {r.text[:300]}")
        return []
    items = r.json()
    print(f"  Got {len(items)} items.")
    return items


def normalise(t):
    text = t.get("text") or t.get("fullText") or t.get("full_text") or ""
    return {
        "id": str(t.get("id") or t.get("tweetId") or t.get("rest_id") or ""),
        "text": text.strip(),
        "url": t.get("url") or t.get("twitterUrl") or "",
        "author": (t.get("author") or {}).get("userName") or t.get("username") or "",
        "likes": int(t.get("likeCount") or t.get("favorite_count") or 0),
        "type": (t.get("type") or "").lower(),
    }


def is_substantive(tweet_text):
    """Filter out fortune-cookie motivational one-liners.
    Good sources: contain numbers, dollar amounts, company names, announcements, specific claims.
    Bad sources: generic motivational quotes, one-liners under 100 chars with no specifics."""
    text = tweet_text.strip()

    # Too short to contain substance
    if len(text) < 100:
        # Unless it contains a number or dollar amount (could be a punchy announcement)
        if not re.search(r'\$[\d,]+|\d{2,}', text):
            return False

    # Motivational fortune-cookie indicators
    fortune_cookie_patterns = [
        r"^(the |a )?(best|only|real|true|greatest|biggest) (way|thing|secret|key|mistake)",
        r"dreams die",
        r"(success|failure|greatness|growth) (is|isn't|comes from|requires)",
        r"^(stop|start|never|always) \w+ing",
        r"the (hard|easy|simple|real) (truth|part|thing)",
        r"(most people|99%|everyone) (don't|won't|can't|never)",
    ]
    lower = text.lower()
    for pattern in fortune_cookie_patterns:
        if re.search(pattern, lower):
            return False

    return True


def filter_usable(items, used_ids):
    out = []
    for raw in items:
        t = normalise(raw)
        if not t["id"] or t["id"] in used_ids:
            continue
        if not t["text"] or len(t["text"]) < MIN_NEWS_LENGTH:
            continue
        if t["type"] in ("retweet", "reply") or t["text"].startswith("RT @") or t["text"].startswith("@"):
            continue
        if not is_substantive(t["text"]):
            print(f"  Skipping fortune cookie: \"{t['text'][:80]}...\"")
            continue
        out.append(t)
    out.sort(key=lambda x: x["likes"], reverse=True)
    return out


# --- generation ---

def validate_post(post):
    problems = []
    if len(post) > 280:
        problems.append(f"is {len(post)} chars, max 280")
    if "\u2014" in post:
        problems.append("em dash")
    if "\u2013" in post:
        problems.append("en dash")
    if len(post) > 80 and "\n\n" not in post:
        problems.append("missing line breaks (use \\n\\n between sentences)")
    lower = post.lower()
    for phrase in BANNED_SUBSTRINGS:
        if phrase in lower:
            problems.append(f"banned: '{phrase}'")
    for pattern, desc in BANNED_REGEX_PATTERNS:
        if re.search(pattern, post, flags=re.IGNORECASE):
            problems.append(f"pattern: {desc}")
    return len(problems) == 0, problems


def generate_thread(source_tweet):
    """Generate a main post + reply thread from a source tweet."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    source = (
        f"Source: @{source_tweet['author']}\n"
        f"Tweet: {source_tweet['text']}\n"
        f"URL: {source_tweet['url']}"
    )

    instruction = (
        f"{source}\n\n"
        f"Write the MAIN POST (scroll-stop with open loop) and the REPLY (insight that completes the loop). "
        f"Output the JSON object.\n\n"
        f"Output: {{\"main\": \"...\", \"reply\": \"...\"}}"
    )

    last_result = None
    feedback = ""

    for attempt in range(3):
        msg = instruction
        if feedback:
            msg = f"PREVIOUS FAILED:\n{feedback}\n\nRewrite.\n\n" + msg

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": msg}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)

        try:
            data = json.loads(raw)
            main = data["main"]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Parse error attempt {attempt + 1}: {e}")
            continue

        # Validate main post
        ok_main, probs_main = validate_post(main)
        # Additional check: hooks must never end with a full stop
        if main.rstrip().endswith(".") and not main.rstrip().endswith("Show more"):
            probs_main.append("hook ends with full stop (must end with colon, mid-sentence, or 'Show more')")
            ok_main = False

        reply = data.get("reply", "")
        ok_reply, probs_reply = validate_post(reply)

        if ok_main and ok_reply:
            return main, reply

        problems = []
        if not ok_main:
            problems.extend(f"main: {p}" for p in probs_main)
        if not ok_reply:
            problems.extend(f"reply: {p}" for p in probs_reply)
        feedback = "\n".join(f"- {p}" for p in problems)
        last_result = (main, reply)

    return last_result


# --- typefully ---

def get_typefully_social_set():
    if TYPEFULLY_SOCIAL_SET_ID:
        return TYPEFULLY_SOCIAL_SET_ID
    print("  TYPEFULLY_PERSONAL_SOCIAL_SET_ID not set.")
    return None


def push_to_typefully_as_draft(main_text, reply_text, cta_text=None):
    """Push as DRAFT for manual review. Not auto-published."""
    social_set_id = get_typefully_social_set()
    if not social_set_id:
        return None

    posts = [
        {"text": main_text},
        {"text": reply_text},
    ]
    if cta_text:
        posts.append({"text": cta_text})

    payload = {
        "platforms": {
            "x": {
                "enabled": True,
                "posts": posts,
            },
        },
        # No publish_at means it stays as a draft for review
    }

    r = requests.post(
        f"https://api.typefully.com/v2/social-sets/{social_set_id}/drafts",
        headers={
            "Authorization": f"Bearer {TYPEFULLY_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )

    if r.status_code in (200, 201):
        data = r.json()
        print(f"    Draft created ({len(posts)}-post thread)")
        return data.get("share_url") or data.get("id")

    print(f"  Typefully error {r.status_code}: {r.text[:300]}")
    return None


# --- commit ---

def commit_state():
    if not os.path.exists(POSTED_LOG):
        return
    subprocess.run(["git", "config", "user.name", "Personal Engine Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@noreply"], check=True)
    subprocess.run(["git", "add", POSTED_LOG], check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode
    if diff == 0:
        return
    msg = f"Personal engine run: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    subprocess.run(["git", "commit", "-m", msg], check=True)
    for attempt in range(3):
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode == 0:
            return
        subprocess.run(["git", "pull", "--rebase", "--autostash"], check=False)


# --- main ---

def main():
    print("=" * 55)
    print("  Personal X Engine - Lewis Waldron")
    print(f"  {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Seeds: {len(SEED_HANDLES)} handles")
    print(f"  Target: {POSTS_PER_RUN} draft threads")
    print("=" * 55)

    posted_log = load_posted_log()
    used_ids = set(posted_log.get("source_ids", []))

    raw = fetch_tweets(SEED_HANDLES)
    if not raw:
        print("\nNo tweets returned. Exiting.")
        sys.exit(0)

    usable = filter_usable(raw, used_ids)
    print(f"\nUsable: {len(usable)}")

    if not usable:
        print("Nothing fresh. Exiting.")
        sys.exit(0)

    drafts_created = 0

    for source in usable[:POSTS_PER_RUN]:
        print(f"\n{'-'*55}")
        print(f"  @{source['author']} ({source['likes']} likes)")
        print(f"  \"{source['text'][:120]}{'...' if len(source['text']) > 120 else ''}\"")

        # Determine if this thread gets a CTA as 3rd post
        posted_log["thread_count"] = posted_log.get("thread_count", 0) + 1
        use_cta = posted_log["thread_count"] % CTA_EVERY_N == 0

        result = generate_thread(source)
        if not result:
            print("  Failed to generate. Skipping.")
            continue

        main_post, reply_post = result
        cta = random.choice(get_cta_lines()) if use_cta else None

        print(f"\n  Post 1 ({len(main_post)} chars): {main_post.replace(chr(10), ' ')[:80]}...")
        print(f"  Post 2 ({len(reply_post)} chars): {reply_post.replace(chr(10), ' ')[:80]}...")
        if cta:
            print(f"  Post 3 (CTA): {cta[:60]}...")

        tid = push_to_typefully_as_draft(main_post, reply_post, cta_text=cta)
        if tid:
            drafts_created += 1
            print(f"    Typefully: {tid}")
            posted_log["source_ids"].append(source["id"])
        else:
            print("    Failed to push.")

    save_posted_log(posted_log)
    commit_state()

    print(f"\n{'='*55}")
    print(f"[OK] Personal engine done.")
    print(f"     Sources considered: {len(usable[:POSTS_PER_RUN])}")
    print(f"     Drafts created: {drafts_created}")


if __name__ == "__main__":
    main()
