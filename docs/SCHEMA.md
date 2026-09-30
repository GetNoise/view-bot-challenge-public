# Schema

Five tables in one SQLite file, `db/view-bot.sqlite`. The names and the important columns
match the production Noise database (which runs Postgres), so what you learn here carries
over. Three conventions cover the type differences:

- Timestamps are text in ISO 8601 UTC, for example `2026-09-22T14:00:00Z`. They sort
  correctly as strings and SQLite's `datetime()`, `julianday()`, and `unixepoch()` parse them.
- Booleans are integers, `0` or `1`.
- `content.status` is text with a check constraint instead of a Postgres enum.

The DDL is in `db/schema.sql`.

## organizations

Brands that pay creators for views on posts that promote them.

| column | type | notes |
|---|---|---|
| id | integer | primary key |
| name | text | |
| slug | text | unique |
| created_at | text | ISO 8601 UTC |

## users

Creators.

| column | type | notes |
|---|---|---|
| id | integer | primary key |
| created_at | text | when the creator joined Noise |
| geo | text | two-letter country code, may be null |
| level | integer | creator tier, 1 (new) to 5 (established) |

## social_accounts

A creator's TikTok or Instagram account. A creator can have more than one.

| column | type | notes |
|---|---|---|
| id | integer | primary key |
| user_id | integer | references users |
| platform | text | `tiktok` or `instagram` |
| handle | text | unique per platform |
| created_at | text | when the account was linked |

## content

One row per post. The counters hold the latest values we scraped.

| column | type | notes |
|---|---|---|
| id | integer | primary key |
| content_id | text | the platform's own id for the post, unique |
| url | text | unique |
| platform | text | `tiktok` or `instagram` |
| user_id | integer | references users |
| social_account_id | integer | references social_accounts |
| promoting_organization_id | integer | references organizations, null when the post promotes no brand |
| created_at | text | when the post went live on the platform |
| discovery_source | text | how we found the post: `profile_scan` or `app_submit` |
| title | text | caption |
| image | text | thumbnail url |
| views, likes, comments, shares, bookmarks | integer | latest cumulative counters |
| status | text | `approved`, `in_review`, or `rejected`; every row starts as `approved` |
| status_changed_at | text | set this when you change status |
| rejected_at | text | set this when status becomes `rejected` |
| reviewed | integer | 1 once a human has looked at the post |

Posts with a null `promoting_organization_id` are a creator's ordinary posts. We scrape
them too, because they tell us what a creator's normal numbers look like.

## content_history

One row per scrape that observed new views on a post.

| column | type | notes |
|---|---|---|
| id | integer | primary key |
| content_id | integer | references content (the `id`, not the platform `content_id`) |
| created_at | text | when the scrape ran |
| sync_job_id | text | the scrape batch this row came from |
| views, likes, comments, shares, bookmarks | integer | cumulative counters at scrape time |
| new_views, new_likes, new_comments, new_shares, new_bookmarks | integer | change since the previous row for this post, floored at zero |

Rules the ingestion pipeline follows:

1. Counters are cumulative. `views` on a history row is the total at that moment.
2. `new_*` is the difference from the previous row for the same post. The first row for a
   post carries its full counters as `new_*`.
3. A scrape that sees no new views writes no row. Gaps between rows are normal.
4. Many posts get scraped in one batch. Rows from one batch share a `sync_job_id`.
5. Scrapes run at irregular intervals. A gap of four hours is typical. A gap of a day happens.

## Access

The database is the file `db/view-bot.sqlite`. Anything that can open SQLite can read and
write it: the `sqlite3` command line tool, `better-sqlite3` or `node:sqlite` in Node,
`sqlite3` in Python, and so on.

- Reads can happen anywhere in your stack.
- Status changes must go through your server. The browser never touches the file.
- Foreign keys are declared but SQLite only enforces them when a connection runs
  `pragma foreign_keys = on`. Do that in your app.
- You may add tables, views, or indexes. If you add schema, keep the SQL in your repo so
  we can reproduce it.
- `scripts/build-db.sh --reset` rebuilds the file from `db/schema.sql` and `db/seed.sql`
  if you want to start over.

## Timeline

The dataset is frozen. The first post went live on 2026-08-28. The last scrape ran at
2026-09-27 00:00 UTC. Treat 2026-09-28 as today.
