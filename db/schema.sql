-- View-bot challenge schema (SQLite).
-- A slim mirror of the Noise content tables. Column names match production
-- where they matter so the shape of the data is the shape you would meet on
-- the job. See docs/SCHEMA.md for what each column means.
--
-- Conventions, because SQLite has fewer types than Postgres:
--   * timestamps are text, ISO 8601 in UTC, e.g. 2026-09-22T14:00:00Z
--   * booleans are integers, 0 or 1
--   * content.status is text constrained to approved / rejected / in_review

pragma foreign_keys = on;

-- Brands that pay creators for views on posts that promote them.
create table organizations (
  id          integer primary key,
  name        text not null,
  slug        text not null unique,
  created_at  text not null default (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Creators. `level` is the creator tier (1 = new, 5 = established).
create table users (
  id          integer primary key,
  created_at  text not null default (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  geo         text,
  level       integer not null default 1
);

-- A creator's TikTok or Instagram account. One creator can have several.
create table social_accounts (
  id          integer primary key,
  user_id     integer not null references users (id) on delete cascade,
  platform    text not null check (platform in ('tiktok', 'instagram')),
  handle      text not null,
  created_at  text not null default (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  unique (platform, handle)
);

-- One row per post. The counters are the latest values we have scraped.
-- `promoting_organization_id` is null for a creator's ordinary post that does
-- not promote a brand. Those posts still get scraped and still appear here.
create table content (
  id                        integer primary key,
  content_id                text not null unique,
  url                       text not null unique,
  platform                  text not null check (platform in ('tiktok', 'instagram')),
  user_id                   integer not null references users (id) on delete cascade,
  social_account_id         integer not null references social_accounts (id) on delete cascade,
  promoting_organization_id integer references organizations (id) on delete set null,
  created_at                text not null default (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  discovery_source          text,
  title                     text,
  image                     text,
  views                     integer not null default 0,
  likes                     integer not null default 0,
  comments                  integer not null default 0,
  shares                    integer not null default 0,
  bookmarks                 integer not null default 0,
  status                    text not null default 'approved'
                              check (status in ('approved', 'rejected', 'in_review')),
  status_changed_at         text,
  rejected_at               text,
  reviewed                  integer not null default 0 check (reviewed in (0, 1))
);

-- One row per scrape that observed a change. Counters are cumulative at the
-- time of the scrape. The `new_*` columns are the delta from the previous row
-- for the same post, floored at zero. A scrape that sees no new views writes
-- no row at all.
create table content_history (
  id            integer primary key,
  content_id    integer not null references content (id) on delete cascade,
  created_at    text not null default (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  sync_job_id   text not null,
  views         integer not null default 0,
  likes         integer not null default 0,
  comments      integer not null default 0,
  shares        integer not null default 0,
  bookmarks     integer not null default 0,
  new_views     integer not null default 0,
  new_likes     integer not null default 0,
  new_comments  integer not null default 0,
  new_shares    integer not null default 0,
  new_bookmarks integer not null default 0
);

create index content_history_content_id_created_at_idx
  on content_history (content_id, created_at);
create index content_history_sync_job_id_idx
  on content_history (sync_job_id);
create index content_promoting_organization_id_idx
  on content (promoting_organization_id);
create index content_status_idx
  on content (status);
create index content_user_id_idx
  on content (user_id);
