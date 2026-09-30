# Noise take-home: find the view bots

Thanks for taking this on. We care more about how you reason than
how polished the result looks.

## The setting

Noise pays creators for the views their posts earn while promoting a brand. Some people try
to game that with purchased views. Every fake view we pay for is money a brand did not get
value for, and a creator who played fair gets a smaller share.

You have a database of about 620 posts from 74 creators, scraped over a month. Some of those
posts have bought views. Some just did well. Your job is to tell them apart and give a
reviewer the tools to act.

## What you get

- This repo.
- `db/view-bot.sqlite`, the database. It is a plain SQLite file, already seeded, ready to
  open with `sqlite3 db/view-bot.sqlite` or any SQLite library. No credentials, no services.
- `docs/SCHEMA.md`, which explains every table and how the scrape pipeline writes rows.
  Read it first. The rules about cumulative counters and `new_*` deltas matter.
- `db/schema.sql` and `db/seed.sql`, which built the database. `scripts/build-db.sh --reset`
  rebuilds it from scratch if you want a clean copy.
- `scripts/verify-seed.sql`, a sanity check that the build script runs for you.

## Time: one hour, fork to last commit

You have one hour. The clock starts when you fork this repo and stops when your last
commit lands on GitHub. We read the fork time and the push times from GitHub, not the
dates inside your commits, and we read the timestamps in your Claude Code transcripts
alongside them.

Once you fork, you are on the clock. Anything pushed after the hour is not part of the
submission.

## What to build

A web app, live on a public URL, that a reviewer at Noise could use. It must:

1. List the posts you think are suspicious, with the reasons. A reviewer should
   understand at a glance why a post is on the list.
2. Show a post's history: how views and engagement moved over time.
3. Let the reviewer set a post to `in_review` or `rejected`, and back to `approved`, and
   persist that to the database.

Ship something. A plain HTML table with a text column of reasons, a list of numbers for the
history, and three buttons is a complete submission. Polish is not what we are looking at.
A beautiful app with no live URL, or one that never got to the status buttons, scores lower
than an ugly one that does all three things. Get it working and deployed first, then spend
whatever is left of the hour on detection quality and your write-up.

Use any language, framework, or hosting you like.

## Claude Code is required

Do the work with [Claude Code](https://claude.com/claude-code), in this repo. This is not
optional. How you work with the tool is half of what we are evaluating, and the transcripts
are how we see it.

1. Open Claude Code in your clone of this repo and build from there. The first time it
   starts it enables a git hook that copies every Claude Code transcript into `chat-logs/`
   and stages it with each commit, as the raw `.jsonl` plus a readable `.txt`. Commit
   normally and the transcripts come along. After your first commit, check that files
   appeared under `chat-logs/claude/`. If they did not, run `scripts/archive-chat-logs.sh`
   and ask us before going further.
2. Leave `chat-logs/` alone. Do not edit, trim, or delete anything in it. Work done outside
   Claude Code, or with the hook disabled, will not show up, and we will treat that as if
   the work was not done.
3. Keep a short decision log in your README. Where Claude proposed something and you
   changed it, say what and why. Where you took its output as is, say that too.
4. After you submit, we spend fifteen minutes on a call walking through your app and your
   flagged list. You explain the choices. Be ready to defend each post you flagged and each
   big post you left alone.

## Constraints

- Status changes must go through your server, not straight from the browser to the file.
  The reviewer's action should still be there after a reload and after a restart.
- Do not commit any hosting credentials or API keys. There are none in this repo; keep it
  that way.
- You may add tables, views, or indexes to the database. Keep the SQL in your repo so we can
  reproduce it.

## What to hand in

1. The live URL.
2. A link to your repo (invite us if it is private), with your Claude Code transcripts
   committed under `chat-logs/`.
3. A README in your repo that covers: how you decided what counts as suspicious, your
   decision log, what you would do with more time, and how to run the project.

Send all three by email as soon as your last commit is pushed. Your submission is whatever
is on GitHub one hour after the fork.

A submission without a live URL, or without Claude Code transcripts in `chat-logs/`, will
not be considered. Those two are the bar to get read at all. Everything else is a matter of
degree.

## How we evaluate

- Detection: which posts you flag, which you leave alone, and why. A post with a lot of
  views is not automatically a bot. A post with few views is not automatically clean.
- The walkthrough: you can explain every flag and every pass in your own words.
- The write path: the status change works, persists, and goes through the server.
- Working with Claude Code: from the transcripts, whether you directed the tool, caught
  its mistakes, and understood what it produced.
- Engineering: the repo runs from its README, secrets stay out of git, the code reads well.
- The UI, last and least: a reviewer can find a post, see why it is flagged, look at its
  history, and act. Function counts. Looks do not.

## Questions

Email the person who sent you this. Questions are welcome. Asking a good one is a plus.
