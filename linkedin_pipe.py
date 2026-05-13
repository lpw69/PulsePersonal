#!/usr/bin/env python3
"""
LinkedIn Pipe - Lewis Waldron / UDG

Strategic authority content for LinkedIn. Takes news events, founder moves,
and economic shifts and extracts distribution/narrative principles.

Different from X engine:
- Longer format (1000-1500 chars)
- Strategic tone, not hyperbole
- CTA in comments, not post body
- 2-3 posts per day (LinkedIn penalises high volume)
- First 3 lines optimised for "see more" fold

Pushes to Typefully as DRAFTS for manual review.

Required secrets:
  ANTHROPIC_API_KEY
  APIFY_API_TOKEN
  TYPEFULLY_API_KEY
  TYPEFULLY_PERSONAL_SOCIAL_SET_ID
  GITHUB_TOKEN  (auto-provided)
"""

import os, re, sys, json, random, datetime, subprocess, requests
import anthropic
import feedparser

# --- env ---
ANTHROPIC_API_KEY       = os.environ["ANTHROPIC_API_KEY"]
APIFY_API_TOKEN         = os.environ["APIFY_API_TOKEN"]
TYPEFULLY_API_KEY       = os.environ["TYPEFULLY_API_KEY"]
TYPEFULLY_SOCIAL_SET_ID = os.environ.get("TYPEFULLY_PERSONAL_SOCIAL_SET_ID", "")

# --- config ---
SEED_HANDLES = [
    # Corporate/enterprise leaders (LinkedIn-credible)
    "satyanadella",
    "JeffBezos",
    "elonmusk",
    "sama",
    "pmarca",
    "chamath",
    "jason",
    # Founders that cross over to LinkedIn audience
    "AlexHormozi",
    "cb_doge",
    "saylor",
]
NEWS_LOOKBACK_HOURS = 24
POSTS_PER_RUN       = 3   # 3 per run, 1 run/day = 3 drafts for review
MIN_NEWS_LENGTH     = 60
POSTED_LOG          = "posted_linkedin.json"

# RSS feeds (heavier on business/economics/policy for LinkedIn)
RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "https://techcrunch.com/feed/",
    "https://fortune.com/feed/",
    "https://www.wired.com/feed/tag/business/latest/rss",
    "https://hnrss.org/best?points=300",
]
RSS_MAX_AGE_HOURS = 24

# CTA config
CTA_EVERY_N = 3  # Every 3rd post gets a soft CTA in the comment
CALENDLY_URL = "https://calendly.com/lewis-underdog-ghostwriting/udg-discovery-call"


# --- system prompt ---

SYSTEM_PROMPT = """You write LinkedIn posts for Lewis Waldron, founder of a content infrastructure company that helps founders and operators build distribution.

THE FORMAT

Every output is ONE LinkedIn post, optionally with a COMMENT (for CTA).

The post has two sections separated by the "see more" fold:

ABOVE THE FOLD (first 1-2 lines, UNDER 140 CHARACTERS): This is ALL most people will see on mobile. It must create an irresistible reason to click "see more." Use the same withholding technique as X: tease the insight, don't reveal it. On desktop users see ~210 chars but always write for mobile first.

BELOW THE FOLD (the rest, 1000-2500 chars): The full story. Reveal what you withheld. Extract the principle. Connect it to distribution, narrative, visibility, or founder leverage. End with a takeaway the reader walks away thinking about.

ABOVE-THE-FOLD TECHNIQUES (remember: under 140 chars)

1. NEWS HOOK + COLON: "NYC's mayor just eliminated a $12B deficit with one announcement:" (65 chars)

2. QUOTE WITHHOLD: "Hormozi just said five words that should terrify every paid media agency:" (73 chars)

3. PATTERN RECOGNITION: "Nadella, Pichai, and Jensen all did the same thing this quarter:" (64 chars)

4. DRAMA + TEASE: "HOLY SHIT. Bezos just mass-fired his entire content team:" (57 chars)

ABOVE THE FOLD MUST NEVER END WITH A FULL STOP. A full stop signals completion. Use a colon to pull them into the rest of the post.

BELOW-THE-FOLD STRUCTURE

1. REVEAL: Open with the detail you withheld. The quote, the number, the decision.

2. CONTEXT: Why this matters. What most people miss about it. 2-3 sentences max.

3. PRINCIPLE EXTRACTION: The broader lesson about distribution, narrative, visibility, or founder leverage. This is the part that makes the reader think "I never thought about it that way."

4. APPLICATION: How this applies to the reader. Make it personal. "If you're a founder..." or "The companies getting this right..."

5. TAKEAWAY: One sentence they walk away with. Not a platitude. A specific, opinionated conclusion.

WHO LEWIS IS ON LINKEDIN
- Founder who builds content infrastructure for other founders and operators
- Strategic thinker, not a guru. Shares frameworks, not motivation.
- Speaks from experience building distribution systems that generate 1.5M views/week
- British, global audience. USD for money references.
- NEVER says "automated", "AI-powered", "bot", or "personal branding" publicly
- "Content infrastructure" is the term. Quiet authority, not hype.

VOICE ON LINKEDIN
- Strategic. Every paragraph earns its place.
- Opinionated but reasoned. Takes positions, backs them with specifics.
- Teaches without being condescending. Shows the thinking, not just the conclusion.
- Conversational authority. Like a smart friend who happens to know a lot about distribution.
- NO EM DASHES. NO EN DASHES. Use commas, full stops, colons.
- NO HASHTAGS. NO EMOJI. NO "agree?" prompts.
- NO staccato fragments. Full sentences throughout.
- Use \\n\\n between paragraphs for readability.

NON-NEGOTIABLE RULES

1. Post must be 1000-2500 characters total (optimal engagement range).
2. First paragraph (before first \\n\\n) must be UNDER 140 characters for the mobile "see more" fold. This is the hook. Everything depends on it.
3. First paragraph must NEVER end with a full stop. End with a colon or mid-sentence. A full stop signals completion and kills the pull to click "see more".
4. NO em dashes, en dashes, hashtags, emoji.
5. NO staccato. No "One word. That word. Changes everything." fragments.
6. NO "Not X. Y." antithesis in any form.
7. NO "Most people think" or any AI antipattern.
8. NEVER fabricate quotes or numbers.
9. USD not GBP.
10. Below the fold: use \\n\\n between every paragraph. Each paragraph 1-3 sentences max.
11. Never say "agree?", "thoughts?", "what do you think?" at the end. Those are engagement-bait and LinkedIn is cracking down.

BANNED PHRASES
"Most people think", "Here's the thing", "The real play", "Plot twist", "Real talk", "The bottom line", "This changes everything", "Imagine if", "What if I told you", "Game changer", "But what's actually interesting", "Let me explain", "Here's why", "Here's how", "Here's what this means", "Thread", "Not X. Y." in any form, "isn't about X it's about Y", fragment-then-explanation, "mate", trailing ellipsis, "agree?", "thoughts?", "hot take:", "unpopular opinion:", "personal branding", "automated", "AI-powered", "bot".

OUTPUT
Valid JSON. No code fences.
{"post": "the full linkedin post text", "comment": "the comment text (CTA) or empty string if no CTA this post"}"""


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
    "here's what founders can learn",
    "here's why", "here's how", "here's what this means",
    "automated", "ai-powered", "ai powered", "bot",
    "ai-native", "personal brand", "personal branding",
    "agree?", "thoughts?", "hot take:", "unpopular opinion:",
]

BANNED_REGEX_PATTERNS = [
    (r"\bnot\s+\w+[.,]\s+not\s+\w+", "staccato Not X. Not Y."),
    (r"\.{3,}.{0,30}$", "trailing ellipsis"),
    (r"\.{3,}\s*$", "ellipsis at end"),
    (r"\bno\s+\w+[.!]\s+no\s+\w+", "triple-fragment"),
    (r",\s+not\s+\w+\.\s*$", "antithesis tail"),
    (r"\bthat'?s\s+not\s+.{2,40}[,.]\s+that'?s\s+", "That's not X. That's Y."),
    (r"\bit'?s\s+not\s+.{2,40}[,.]\s+it'?s\s+", "It's not X. It's Y."),
    (r"\bit'?s\s+not[.]\s+it'?s\s+(about|just|really|actually)", "It's not. It's about Y."),
    (r"\bisn'?t\s+about\s+.{2,30}[,.]\s+it'?s\s+about", "isn't about X. It's about Y."),
    (r"\bnot\s+as\s+.{2,30}[.]\s+as\s+", "Not as X. As Y."),
    (r"\bnot\s+because\s+.{2,40}[.]\s+because\s+", "Not because X. Because Y."),
    (r"\bnot\s+the\s+\w+[.]\s*$", "standalone Not the X."),
    (r"(?:^|\n)\s*not\s+\w+[.]\s*(?:\n|$)", "standalone Not X. on own line"),
    (r"\bdon'?t\s+\w+\s+\w+[.]\s+they\s+\w+\s+", "don't X. They Y."),
    (r"\bnot\s+a\s+[\w\s]{2,25}[.]\s+not\s+a\s+", "Not a X. Not a Y."),
    (r"\b\w[\w\s]{2,20}(hide|conceal|mask|obscure)\w*\s+.{2,20}[.]\s+\w[\w\s]{2,20}(expose|reveal|show|uncover)", "parallel hide/expose"),
    (r"\b\w+\s+\w+\.\s+that'?s\s+(how|what|why|when|where)\s+", "fragment-then-explanation"),
    (r"\bmate\b", "uses mate"),
    # Staccato patterns
    (r"(?<=[.!?])\s+\b(\w+\s+){0,4}\w+[.!?]\s+\b(\w+\s+){0,4}\w+[.!?]", "consecutive short-sentence staccato"),
    (r"(?:^|[.!?])\s*[A-Z][\w']{0,15}(\s+\w+){1,3}[.!?]\s+[A-Z][\w']{0,15}(\s+\w+){1,3}[.!?]", "pair staccato"),
    # NUCLEAR: "Not [anything]." as a standalone sentence
    (r"(?:^|\n\n)Not\s+[\w\s,']{2,45}[.]", "standalone 'Not...' sentence fragment"),
    (r"\bnot\s+[\w\s]{2,20},\s*not\s+[\w\s]{2,20}", "not X, not Y in same sentence"),
    (r"\bnot\s+[\w\s]{2,30}[.]\s+(but|just|only|simply|rather)\s+", "Not X. But/Just/Only Y."),
]


# --- state ---

def load_posted_log():
    if not os.path.exists(POSTED_LOG):
        return {"source_ids": [], "post_count": 0}
    try:
        with open(POSTED_LOG) as f:
            data = json.load(f)
            if "post_count" not in data:
                data["post_count"] = 0
            return data
    except (json.JSONDecodeError, OSError):
        return {"source_ids": [], "post_count": 0}


def save_posted_log(log):
    log["source_ids"] = log["source_ids"][-500:]
    with open(POSTED_LOG, "w") as f:
        json.dump(log, f, indent=2)


# --- apify ---

def fetch_tweets(handles, hours=NEWS_LOOKBACK_HOURS):
    since_date = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).strftime("%Y-%m-%d")
    payload = {
        "twitterHandles": handles,
        "maxItems": 30,
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


# --- rss ---

def fetch_rss():
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=RSS_MAX_AGE_HOURS)
    all_items = []

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            source_name = feed.feed.get("title", feed_url)[:30]

            for entry in feed.entries[:10]:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime.datetime(*published[:6])
                    if pub_dt < cutoff:
                        continue

                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                summary = re.sub(r"<[^>]+>", "", summary)[:300]
                link = entry.get("link", "")
                text = f"{title}. {summary}" if summary else title

                all_items.append({
                    "id": f"rss_{hash(link) % 10**10}",
                    "text": text,
                    "url": link,
                    "author": source_name,
                    "likes": 0,
                    "type": "rss",
                })

            print(f"  RSS: {source_name} -> fetched")
        except Exception as e:
            print(f"  RSS error ({feed_url[:40]}): {e}")

    print(f"  RSS total: {len(all_items)} items")
    return all_items


# --- normalise ---

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
    text = tweet_text.strip()
    if len(text) < 100:
        if not re.search(r'\$[\d,]+|\d{2,}', text):
            return False
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
        t = raw if raw.get("type") == "rss" else normalise(raw)
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
    tweets = sorted([i for i in out if i.get("type") != "rss"], key=lambda x: x["likes"], reverse=True)
    rss = [i for i in out if i.get("type") == "rss"]
    merged = []
    for i in range(max(len(tweets), len(rss))):
        if i < len(tweets):
            merged.append(tweets[i])
        if i < len(rss):
            merged.append(rss[i])
    return merged


# --- generation ---

def validate_post(post):
    problems = []
    if len(post) < 600:
        problems.append(f"too short ({len(post)} chars, min 600 for LinkedIn)")
    if len(post) > 3000:
        problems.append(f"too long ({len(post)} chars, max 3000)")
    if "\u2014" in post:
        problems.append("em dash")
    if "\u2013" in post:
        problems.append("en dash")
    lower = post.lower()
    for phrase in BANNED_SUBSTRINGS:
        if phrase in lower:
            problems.append(f"banned: '{phrase}'")
    for pattern, desc in BANNED_REGEX_PATTERNS:
        if re.search(pattern, post, flags=re.IGNORECASE):
            problems.append(f"pattern: {desc}")
    return len(problems) == 0, problems


def validate_above_fold(post):
    """Check the first paragraph (above the fold) is under 140 chars and doesn't end with a full stop."""
    paragraphs = [p for p in post.split("\n\n") if p.strip()]
    if len(paragraphs) < 2:
        return ["post needs at least 2 paragraphs"]
    above = paragraphs[0].strip()
    problems = []
    if len(above) > 140:
        problems.append(f"above-the-fold is {len(above)} chars (max 140 for mobile)")
    if above.endswith("."):
        problems.append("above-the-fold ends with full stop (must end with colon or mid-sentence)")
    return problems


def get_cta_comment():
    return (
        f"We build content infrastructure for founders and operators. "
        f"1.5M views/week average across our clients.\n\n"
        f"If your distribution is inconsistent and you know it should be better, "
        f"book a discovery call here: {CALENDLY_URL}"
    )


def generate_post(source, use_cta=False):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    source_text = (
        f"Source: @{source['author']}\n"
        f"Content: {source['text']}\n"
        f"URL: {source['url']}"
    )

    cta_instruction = ""
    if use_cta:
        cta_instruction = (
            '\n\nThis post should have a CTA comment. Include a "comment" field '
            'with a soft bridge like "Btw, this is the kind of distribution thinking '
            'we help founders implement. Link in the comments for a discovery call." '
            'Keep it under 200 chars. The actual Calendly link will be appended automatically.'
        )

    instruction = (
        f"{source_text}\n\n"
        f"Write a LinkedIn post. 800-1500 characters. "
        f"First 3 lines must hook before the 'see more' fold. "
        f"Don't reveal the key insight above the fold. "
        f"Below the fold: reveal, provide context, extract principle, apply to reader, end with takeaway. "
        f"Use \\n\\n between every paragraph."
        f"{cta_instruction}\n\n"
        f'Output: {{"post": "...", "comment": "..."}}'
    )

    last_result = None
    feedback = ""

    for attempt in range(3):
        msg = instruction
        if feedback:
            msg = f"PREVIOUS FAILED:\n{feedback}\n\nRewrite.\n\n" + msg

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": msg}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)

        try:
            data = json.loads(raw)
            post = data["post"]
            comment = data.get("comment", "")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Parse error attempt {attempt + 1}: {e}")
            continue

        ok, probs = validate_post(post)
        fold_probs = validate_above_fold(post)

        if ok and not fold_probs:
            if use_cta:
                comment = get_cta_comment()
            return post, comment

        all_probs = probs + fold_probs
        feedback = "\n".join(f"- {p}" for p in all_probs)
        last_result = (post, comment if not use_cta else get_cta_comment())
        print(f"  Validation failed (attempt {attempt + 1}):")
        for p in all_probs:
            print(f"    - {p}")

    return last_result


# --- typefully ---

def get_typefully_social_set():
    if TYPEFULLY_SOCIAL_SET_ID:
        return TYPEFULLY_SOCIAL_SET_ID
    print("  TYPEFULLY_PERSONAL_SOCIAL_SET_ID not set.")
    return None


def push_to_typefully_as_draft(post_text, comment_text=""):
    social_set_id = get_typefully_social_set()
    if not social_set_id:
        return None

    # LinkedIn post as draft
    posts = [{"text": post_text}]
    if comment_text:
        posts.append({"text": comment_text})

    payload = {
        "platforms": {
            "linkedin": {
                "enabled": True,
                "posts": posts,
            },
        },
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
        print(f"    LinkedIn draft created")
        return data.get("share_url") or data.get("id")

    print(f"  Typefully error {r.status_code}: {r.text[:300]}")
    return None


# --- commit ---

def commit_state():
    if not os.path.exists(POSTED_LOG):
        return
    subprocess.run(["git", "config", "user.name", "LinkedIn Pipe Bot"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@noreply"], check=True)
    subprocess.run(["git", "add", POSTED_LOG], check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode
    if diff == 0:
        return
    msg = f"LinkedIn pipe run: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    subprocess.run(["git", "commit", "-m", msg], check=True)
    for attempt in range(3):
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode == 0:
            return
        subprocess.run(["git", "pull", "--rebase", "--autostash"], check=False)


# --- main ---

def main():
    print("=" * 55)
    print("  LinkedIn Pipe - Lewis Waldron / UDG")
    print(f"  {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Seeds: {len(SEED_HANDLES)} handles + {len(RSS_FEEDS)} RSS feeds")
    print(f"  Target: {POSTS_PER_RUN} draft posts")
    print("=" * 55)

    posted_log = load_posted_log()
    used_ids = set(posted_log.get("source_ids", []))

    raw_tweets = fetch_tweets(SEED_HANDLES)
    raw_rss = fetch_rss()
    all_items = raw_tweets + raw_rss

    if not all_items:
        print("\nNo content. Exiting.")
        sys.exit(0)

    usable = filter_usable(all_items, used_ids)
    print(f"\nUsable: {len(usable)}")

    if not usable:
        print("Nothing fresh. Exiting.")
        sys.exit(0)

    drafts_created = 0

    for source in usable[:POSTS_PER_RUN]:
        print(f"\n{'-'*55}")
        print(f"  @{source['author']} ({source.get('likes', 0)} likes)")
        print(f"  \"{source['text'][:120]}{'...' if len(source['text']) > 120 else ''}\"")

        posted_log["post_count"] = posted_log.get("post_count", 0) + 1
        use_cta = posted_log["post_count"] % CTA_EVERY_N == 0

        result = generate_post(source, use_cta=use_cta)
        if not result:
            print("  Failed to generate. Skipping.")
            continue

        post, comment = result

        print(f"\n  Post ({len(post)} chars): {post[:100]}...")
        if comment:
            print(f"  Comment: {comment[:80]}...")

        tid = push_to_typefully_as_draft(post, comment)
        if tid:
            drafts_created += 1
            print(f"    Typefully: {tid}")
            posted_log["source_ids"].append(source["id"])
        else:
            print("    Failed to push.")

    save_posted_log(posted_log)
    commit_state()

    print(f"\n{'='*55}")
    print(f"[OK] LinkedIn pipe done.")
    print(f"     Sources considered: {len(usable[:POSTS_PER_RUN])}")
    print(f"     Drafts created: {drafts_created}")


if __name__ == "__main__":
    main()
