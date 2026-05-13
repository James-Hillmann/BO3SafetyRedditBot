import os
import time
import logging
import re
import praw
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

SUBREDDIT = "blackops3"
GUIDE_URL = "https://www.reddit.com/r/blackops3/s/0bAMIZzC4I"
REPLIED_IDS_FILE = "replied_ids.txt"

REPLY_TEMPLATE = """\
It looks like you're asking whether Black Ops 3 is safe to play online. \
Currently, the **official BO3 servers have an active RCE (Remote Code Execution) vulnerability**, \
meaning anyone can potentially execute code on your machine simply by you connecting to the BO3 servers — you don't even need to be in the same lobby as an attacker.

Here's a guide on how to protect yourself and play safely:

**[BO3 Safe Play Guide]({guide_url})**

---
*^(I am a bot. If this reply isn't relevant, please ignore it.)*
""".format(guide_url=GUIDE_URL)

# Patterns that suggest someone is asking about game/server safety
SAFETY_PATTERNS = [
    r"\bis\s+(bo3|black\s*ops\s*3|the\s+game|it)\s+(safe|okay|ok|fine|dangerous|risky)\b",
    r"\b(safe|unsafe|dangerous|risky)\s+to\s+(play|join|go\s+online|connect)\b",
    r"\bcan\s+i\s+(play|go\s+online|still\s+play|safely\s+play)\b",
    r"\bshould\s+i\s+(play|go\s+online|still\s+play|avoid)\b",
    r"\b(rce|remote\s*code\s*execution)\b",
    r"\b(hacked?|exploit(ed|s)?|malware|virus|backdoor)\b.{0,60}\b(bo3|black\s*ops|servers?|online|lobby|lobbies)\b",
    r"\b(bo3|black\s*ops\s*3|servers?|online|lobby|lobbies)\b.{0,60}\b(hacked?|exploit(ed|s)?|malware|virus|backdoor)\b",
    r"\b(is\s+it|are\s+the\s+servers?|are\s+they)\s+(still\s+)?(hacked?|compromised|infected|down|unsafe)\b",
    r"\bplay\s+(bo3|black\s*ops\s*3)\s+(online|safely|safe)\b",
    r"\b(online|servers?)\s+(safe|dangerous|risky|still\s+up|working|okay)\b",
    r"\bstill\s+(safe|okay|fine|playable)\b",
    r"\bshould\s+i\s+worry\b",
    r"\bvulnerability\b",
    r"\bget\s+(hacked?|infected|pwned|rce)\b",
    r"\bwill\s+i\s+(get\s+hacked?|be\s+safe|be\s+okay)\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SAFETY_PATTERNS]


def load_replied_ids() -> set:
    if not os.path.exists(REPLIED_IDS_FILE):
        return set()
    with open(REPLIED_IDS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def save_replied_id(post_id: str) -> None:
    with open(REPLIED_IDS_FILE, "a") as f:
        f.write(post_id + "\n")


def is_safety_question(text: str) -> bool:
    return any(pattern.search(text) for pattern in COMPILED_PATTERNS)


def should_reply(submission, replied_ids: set) -> bool:
    if submission.id in replied_ids:
        return False
    if submission.author and submission.author.name.lower() == os.getenv("REDDIT_USERNAME", "").lower():
        return False
    combined_text = f"{submission.title} {submission.selftext}"
    return is_safety_question(combined_text)


def run_bot():
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "BO3SafetyBot/1.0"),
    )

    subreddit = reddit.subreddit(SUBREDDIT)
    replied_ids = load_replied_ids()

    log.info("Bot started. Monitoring r/%s for safety questions...", SUBREDDIT)

    while True:
        try:
            for submission in subreddit.stream.submissions(skip_existing=True):
                if should_reply(submission, replied_ids):
                    log.info("Matched post: %s (id: %s)", submission.title, submission.id)
                    submission.reply(REPLY_TEMPLATE)
                    replied_ids.add(submission.id)
                    save_replied_id(submission.id)
                    log.info("Replied to post id: %s", submission.id)
                    # Be a good bot citizen — avoid rate limit hammering
                    time.sleep(10)

        except praw.exceptions.APIException as e:
            log.warning("Reddit API error: %s — waiting 60s", e)
            time.sleep(60)
        except Exception as e:
            log.error("Unexpected error: %s — restarting stream in 30s", e)
            time.sleep(30)


if __name__ == "__main__":
    run_bot()
