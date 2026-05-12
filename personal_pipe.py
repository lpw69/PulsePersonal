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
    "GaryVee",
    "naval",
    "paulg",
    "sama",
    "balajis",
    "gregisenberg",
    "dharmesh",
    "levelsio",
    "SahilBloom",
]
NEWS_LOOKBACK_HOURS = 24
POSTS_PER_RUN       = 3   # generates 3 draft threads per run for you to review
MIN_NEWS_LENGTH     = 60
POSTED_LOG          = "posted_sources.json"

# CTA config
CTA_EVERY_N = 3  # every 3rd thread gets a distribution sell in the reply
TYPEFORM_URL = ""  # set this once your typeform is live


# --- system prompt ---

SYSTEM_PROMPT = """You write two-part X threads for Lewis Waldron, a founder who builds agentic content infrastructure for other founders and operators.

THE FORMAT

Every output is TWO posts:
1. MAIN POST (the hook): reacts to something a big-name founder just said or did. Extracts a principle. Ends with an OPEN LOOP that makes people click "see more" or expand the thread.
2. REPLY POST (the payoff): completes the thought. Connects the principle to distribution, content, or building in public. This is where the insight lives.

THE OPEN LOOP

The main post MUST end with an incomplete thought that pulls people into the reply. Techniques:
- "The part nobody talks about..." (curiosity gap)
- "But here's what he actually meant by that." (reframe tease)
- "What this tells you about 2026:" (list tease)
- "The founders who get this are doing something different." (tribe tease)
- Just end mid-thought with natural trailing off before the insight lands

The reader should feel: "I need to see the rest of this."

THE REPLY

The reply completes the open loop AND transitions to a broader insight about distribution, content, or building audience. It should feel like earned wisdom, not a pitch. The reader should walk away thinking "this person understands something I don't."

WHO LEWIS IS
- Founder who builds agentic content systems for other founders
- Left defence consulting 18 months ago, built an agency billing in USD
- Pragmatic, opinionated, anti-bullshit, not a guru
- Speaks from experience: built these systems, runs them, sees the results
- British but writes for a global audience (use USD not GBP)

VOICE
- Direct. No fluff. Every sentence earns its place.
- Opinionated but backs it with specifics.
- Not trying to impress. Sharing what he's actually seeing.
- Mild swagger but grounded. "I built this, here's what happened" not "I'm a genius".
- NO EM DASHES. NO EN DASHES. Use commas, full stops, colons.
- NO HASHTAGS.
- NO "most people think" or any AI antipattern.

NON-NEGOTIABLE RULES

1. MAIN POST: max 280 characters. Must end with an open loop.
2. REPLY POST: max 280 characters. Must complete the open loop and land an insight.
3. Both posts must have line breaks (\\n\\n) between beats if over 80 chars.
4. Max 2-3 short paragraphs per post.
5. NEVER fabricate quotes. If the source said something, use their words. If you're paraphrasing, make it clear.
6. USD not GBP for all money references.
7. NO em dashes, en dashes, hashtags.

OPENER STYLES FOR THE MAIN POST

A. QUOTE REACTION (40%): Lead with what the person said, then react.
   "Elon Musk: 'The best marketing is a great product.'\\n\\nHe posts 40 times a day. Think about that for a second."

B. ACTION OBSERVATION (30%): Lead with what they DID, not said.
   "Hormozi spent $2.4M on media before he had product-market fit.\\n\\nSounds insane. Until you see what happened next."

C. PATTERN RECOGNITION (20%): Connect what they did to a trend.
   "Bezos, Zuckerberg, and Hormozi all did the same thing this year.\\n\\nNone of them launched a product. All of them launched content."

D. CONTRARIAN REFRAME (10%): Take their point and twist it.
   "Naval says 'learn to sell, learn to build.'\\n\\nBut the founders actually winning in 2026 added a third skill nobody talks about."

REPLY STYLES

A. PRINCIPLE + APPLICATION: State the extracted principle, then show how it applies.
   "Distribution is the moat now. The product is table stakes.\\n\\nThe founders building content engines are acquiring customers at 1/10th the cost. And they never turn off."

B. PERSONAL EXPERIENCE: Connect to something Lewis has seen or built.
   "We built a system that does this for founders. 10+ posts a day in their voice, across every platform, while they sleep.\\n\\nThe ones running it aren't competing on product anymore. They're competing on attention."

C. FUTURE IMPLICATION: Project forward to what this means.
   "By 2027 every serious founder will have a content engine running alongside their product.\\n\\nThe ones starting now have a 2-year head start on everyone who's still 'thinking about it.'"

BANNED PHRASES
"Most people think", "Here's the thing", "The real play", "Plot twist", "Real talk", "The bottom line", "This changes everything", "Imagine if", "What if I told you", "Game changer", "Not X. Not Y." staccato, "That's not X. That's Y." antithesis, "It's not about X it's about Y", fragment-then-explanation rhythms, "mate", trailing ellipsis on the main post (open loops use incomplete sentences, not "...").

OUTPUT
Valid JSON. No code fences.
{"main": "the main post text", "reply": "the reply post text"}"""


# --- CTA bank for distribution sell (replaces the normal reply every Nth thread) ---

CTA_REPLIES = [
    "If you're a founder doing $500k+ and your content is inconsistent, we should talk.\\n\\nBuilt a system that fixes this permanently. Runs 24/7 in your voice. DM me.",
    "We build content engines for founders. Agentic, always-on, sounds like you not a chatbot.\\n\\nIf you want to see how it works, DM me or check the link in bio.",
    "Distribution is the one thing you can't fake at scale. You either have the system or you don't.\\n\\nWe build that system for founders. Bio if you want the details.",
    "Most founders post when they remember to. The ones winning post every day because they built the infrastructure.\\n\\nWe build that infrastructure. DM me if you want to see it.",
    "The founders we work with went from posting twice a week to 10x a day. Same voice. Same quality. Zero extra hours.\\n\\nIf that sounds relevant, bio link or DM.",
]


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
    (r"\b\w+\s+\w+\.\s+that'?s\s+(how|what|why|when|where)\s+", "fragment-then-explanation"),
    (r"\bmate\b", "uses mate"),
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
        problems.append("missing line break")
    paragraphs = [p for p in post.split("\n\n") if p.strip()]
    if len(paragraphs) > 3:
        problems.append(f"{len(paragraphs)} paragraphs, max 3")
    lower = post.lower()
    for phrase in BANNED_SUBSTRINGS:
        if phrase in lower:
            problems.append(f"banned: '{phrase}'")
    for pattern, desc in BANNED_REGEX_PATTERNS:
        if re.search(pattern, post, flags=re.IGNORECASE):
            problems.append(f"pattern: {desc}")
    return len(problems) == 0, problems


def generate_thread(source_tweet, use_cta=False):
    """Generate a main post + reply thread from a source tweet."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    source = (
        f"Source: @{source_tweet['author']}\n"
        f"Tweet: {source_tweet['text']}\n"
        f"URL: {source_tweet['url']}"
    )

    if use_cta:
        instruction = (
            f"{source}\n\n"
            f"Write the MAIN POST only (the hook with open loop). "
            f"I will provide the reply separately. Output JSON with main only.\n\n"
            f"Output: {{\"main\": \"...\"}}"
        )
    else:
        instruction = (
            f"{source}\n\n"
            f"Write both the MAIN POST (hook with open loop) and the REPLY (payoff with insight). "
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

        if use_cta:
            reply = random.choice(CTA_REPLIES)
            if ok_main:
                return main, reply
            feedback = "\n".join(f"- main: {p}" for p in probs_main)
            last_result = (main, reply)
            continue

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


def push_to_typefully_as_draft(main_text, reply_text):
    """Push as DRAFT for manual review. Not auto-published."""
    social_set_id = get_typefully_social_set()
    if not social_set_id:
        return None

    payload = {
        "platforms": {
            "x": {
                "enabled": True,
                "posts": [
                    {"text": main_text},
                    {"text": reply_text},
                ],
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
        print(f"    Draft created (2-post thread)")
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

        # Determine if this thread gets a CTA reply
        posted_log["thread_count"] = posted_log.get("thread_count", 0) + 1
        use_cta = posted_log["thread_count"] % CTA_EVERY_N == 0

        result = generate_thread(source, use_cta=use_cta)
        if not result:
            print("  Failed to generate. Skipping.")
            continue

        main_post, reply_post = result

        print(f"\n  Main ({len(main_post)} chars): {main_post.replace(chr(10), ' ')[:80]}...")
        print(f"  Reply ({len(reply_post)} chars): {reply_post.replace(chr(10), ' ')[:80]}...")
        if use_cta:
            print(f"  [CTA thread #{posted_log['thread_count']}]")

        tid = push_to_typefully_as_draft(main_post, reply_post)
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
