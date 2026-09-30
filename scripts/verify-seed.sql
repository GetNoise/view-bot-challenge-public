-- Sanity checks for the seeded dataset.
-- Run with:  sqlite3 db/view-bot.sqlite < scripts/verify-seed.sql
-- (scripts/build-db.sh runs this for you.)
-- Every check should print ok = 1.

.headers on
.mode column

select 'organizations' as table_name, count(*) as rows from organizations union all
select 'users',           count(*) from users union all
select 'social_accounts', count(*) from social_accounts union all
select 'content',         count(*) from content union all
select 'content_history', count(*) from content_history;

select min(created_at) as first_post, max(created_at) as last_post
from content;

select min(created_at) as first_scrape, max(created_at) as last_scrape
from content_history;

-- Every post's counters equal its most recent history row.
select count(*) = 0 as ok, 'content counters match last history row' as check_name
from content c
join (
  select content_id, views, likes, comments, shares, bookmarks,
         row_number() over (partition by content_id order by created_at desc) as rn
  from content_history
) h on h.content_id = c.id and h.rn = 1
where c.views <> h.views or c.likes <> h.likes or c.comments <> h.comments
   or c.shares <> h.shares or c.bookmarks <> h.bookmarks;

-- Every post has at least one history row.
select count(*) = 0 as ok, 'every post has history' as check_name
from content c
where not exists (select 1 from content_history h where h.content_id = c.id);

-- new_views equals the delta from the previous row (floored at zero).
select count(*) = 0 as ok, 'new_views is the delta from the previous row' as check_name
from (
  select new_views,
         max(views - coalesce(lag(views) over (partition by content_id order by created_at), 0), 0) as expected
  from content_history
) x
where new_views <> expected;

-- Foreign keys all resolve.
select count(*) = 0 as ok, 'foreign keys resolve' as check_name
from pragma_foreign_key_check;
