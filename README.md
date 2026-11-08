# Linkedin-Posting-Automation
Hey for anyone looking at this project, its meant to streamline the process of going to event and drafting a Linkedin post without taking too much time to perfect the wordings, un-AI the post and also make creating Linkedin post easy.

## How it works
A private Telegram bot. During an event you send it notes and photos. Afterwards it asks
3 questions and drafts a short LinkedIn post, a long LinkedIn post and an X post in your
own voice, using only what you sent. Names or numbers it can't find in your notes are
flagged for you to check. You copy-paste the post yourself.

## Setup
1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Get your numeric Telegram user ID from [@userinfobot](https://t.me/userinfobot).
3. Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).
4. Copy `.env.example` to `.env` and fill in the values.
5. Put 5-10 past posts in `style_samples/` as `.txt` files.
6. Install and run:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python -m bot.main
   ```

## Commands
- `/event <name>` start capturing
- `/done` answer 3 questions and get drafts
- `/redraft` regenerate the latest drafts
- `/cancel` drop the open event

## Tests
`python -m pytest`
