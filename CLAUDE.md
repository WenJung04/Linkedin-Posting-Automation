# Project: Post-event LinkedIn recap bot (Telegram, Python)

## What this is
A personal Telegram bot that turns in-the-moment event captures (photos, voice notes,
typed bullets) into a LinkedIn post draft written in my own voice. I copy-paste the
final post into LinkedIn myself. No LinkedIn API in v1.

## About me (the user)
- Final-year / fresh-graduate IT student in Malaysia, job hunting now. Need income soon.
- Targeting remote BD or entry-level dev roles in crypto/web3 (USD 2-3k/month).
- Can spend about 10 hours a week on projects. The job hunt comes first.
- Python is my preferred language for this project.
- I procrastinate and get exhausted after events, so posts get delayed. The
  problem is activation energy, not writing quality.

## Problem
After events I have the ideas but delay posting because writing it up neatly feels slow.
Delayed posts lose relevance and visibility. Consistent posting helps my job hunt
(crypto hiring happens on X and by word of mouth).

## Decision: personal tool, not a business
Research showed the space is saturated:
- Supergrow (voice note to LinkedIn post, about $19-29/mo), Taplio ($39-149/mo),
  AuthoredUp, MagicPost, TalkToPost, Yap-It.
- Several n8n templates already do Telegram -> AI draft -> approve -> publish,
  including one for event notes.
- Prices and revenue figures are conflicting or self-reported.
Build it for myself and as a portfolio piece. Do not over-invest time.

## Key research findings (treat as directional, some unverified)
- Roughly half of long LinkedIn posts are likely AI-written (Originality.ai).
- LigoSocial (134k posts): AI-sounding posts got about 22% less engagement than the
  same author's other posts. Claims of an 80% reach penalty are unverified.
- Implication: the value is preserving MY facts and MY voice, not generic generation.
- LinkedIn personal posting uses the `w_member_social` scope, but sources conflict on
  partner approval and I found nothing on whether the terms allow automated posting.
  Read LinkedIn's API terms before ever automating. v1 = copy-paste only.
- About 10.9M LinkedIn users in Malaysia (NapoleonCat estimate).

## Usage context (decided 2026-10-29)
- About 2 events a month. Purpose: portfolio piece for **dev roles**, plus real use.
- Success metric: post within 48 hours for 4 of my next 5 events, with 5 minutes or
  less of editing per draft.
- Cost target: free. Runs on my laptop (not a phone, not a server) for v1.

## Design
1. `/event <name>` starts a capture session. One active session at a time.
2. During the event I send photos and typed bullet thoughts. Voice notes are out of v1.
3. `/done` makes the bot ask 3 questions: the one takeaway, who I met, what I'll do next.
   Any question can be skipped ("skip").
4. Bot drafts using ONLY what I provided. Never invent facts, names or numbers.
   - Use 5-10 of my past posts (in `style_samples/`) as voice examples.
   - Outputs: short LinkedIn post, long LinkedIn post (plain text, no markdown,
     under 3000 chars, hook in the first two lines), an X post (280 chars or less),
     and the best photo with a one-line reason.
   - Avoid generic AI phrasing, hype and filler hashtags.
   - Fact check: flag any names or numbers in the draft that are not in my inputs.
5. `/redraft` regenerates the latest draft (also the retry path if the LLM call fails).
6. Reminder in the output: get consent before posting other people's faces.

### Later (v1.1, after the core flow works)
- Auto-close a session after a few hours with no captures, then ask the 3 questions.
- Reply-with-feedback to revise a draft ("less formal, mention Ahmad").
- Nudges about 2 hours after the event and next morning. Store due times in SQLite,
  not only in JobQueue memory, and on startup send any nudges missed while the laptop
  was asleep. Timezone: Asia/Kuala_Lumpur.

## Tech decisions
- Python 3.11+, `python-telegram-bot` (async).
- LLM: Google Gemini API free tier (Flash model) via the `google-genai` SDK. The model
  name is configurable (`GEMINI_MODEL`) because free-tier models change. Keep all LLM
  calls behind a small provider interface (`bot/llm.py`) so Claude can be swapped in
  if draft quality is not good enough. Free-tier data may be used by Google; accepted.
- SQLite for event sessions, captures, answers and drafts. Photos stored under `data/`.
- Config via environment variables: `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`,
  `GEMINI_MODEL`, `ALLOWED_TELEGRAM_USER_ID` (the bot must ignore everyone except me).
- Never commit secrets. Provide a `.env.example` and a `.gitignore` that excludes `.env`.

## Out of scope for v1
LinkedIn API posting, scheduling, analytics, multi-user support, a web UI, voice notes
(if added later: hosted Whisper-style API, since the laptop should stay light).

## Working agreements for Claude
- Be critical and honest. Say when an idea is weak, crowded or unverified.
- Back market and technical claims with sources, and flag uncertainty.
- Keep scope small: ship a working v1 in one or two sessions, then stop.
- Explain trade-offs briefly and recommend one option rather than listing many.
- Match simple, readable Python. Add tests only for the draft-prompt builder, session
  state logic and the fact check.

## Backlog (separate projects, do not start here)
- Job-triage copilot: paste a job post to get an eligibility verdict for a Malaysian
  applicant, scam and malware red flags, and a fit score.
- Malaysia crypto trust checker: check links, Telegram pitches and exchange names
  against the SC Investor Alert List and known scam patterns (BM, English, Chinese).
  Never state "this is a scam"; report evidence and risk signals only.

## First task
Scaffold the project (structure, dependencies, `.env.example`, `.gitignore`), then
implement `/event`, capture handling, `/done` with the 3 questions, draft generation,
the fact check and `/redraft`.
Ask me for the style samples before tuning the prompt.