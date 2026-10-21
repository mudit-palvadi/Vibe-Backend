# Moving the data from Supabase and Cloudinary to AWS

The app now lives on AWS: the songs and the users are in DynamoDB, the song files
are in S3, and the api runs on Lambda behind CloudFront. This page is the
step by step plan to move the data of the old project over.

Nothing in the old project is deleted by these steps, so the old api keeps
working until the new one is checked.

## What is moved where

| old | new |
| --- | --- |
| the `users` table in Supabase Postgres | the `USER#<id>` items in the `vibe` table |
| the `songs`, `playlists`, `playlist_songs` and `favourites` tables | the `SONG#<id>`, `PLAYLIST#<id>` and `IDX_` items in the same table |
| the song files in Cloudinary | the `songs/<song id>/` objects in the S3 bucket |
| the google login of Supabase | the google login of the app, the `google_sub` column keeps the link |

The user id does not change, so the playlists and the favourites of every user
stay connected to their owner.

## Before you start

You need a `.env` file in the `server` folder with:

```
DATABASE_URL=postgresql+psycopg2://...the old supabase database...
AWS_REGION=ap-south-1
DYNAMODB_TABLE_NAME=vibe
S3_BUCKET=vibestack-mediabucketbcbb02ba-mgtm5ennm3bo
MEDIA_BASE_URL=https://d3hb9a4bci0gq5.cloudfront.net
```

The aws keys come from the login session:

```bash
aws configure export-credentials --profile mudit-palvadi --format env
```

## Step 1: the google id of every user

The old users are looked up by their email today. The new api looks them up by
the id that google gives them, so the column has to be filled in first.

```bash
python scripts/migrate_google_sub.py
```

The script adds the `google_sub` column to the `users` table and fills it in
from the `auth.identities` table of Supabase. A user that never signed in with
google keeps a null value and is looked up by email the first time.

## Step 2: the song files

```bash
python scripts/copy_media_to_s3.py
```

Every audio file and every thumbnail is downloaded from Cloudinary and put into
the bucket under `songs/<song id>/`. The script writes `scripts/media_map.json`
with the new addresses of the files, the next script uses it.

## Step 3: the users

```bash
python scripts/migrate_users_to_dynamodb.py
```

## Step 4: the songs, the playlists and the favourites

```bash
python scripts/migrate_content_to_dynamodb.py
```

The songs get the new addresses of their files from the media map, the playlists
keep their songs, and the favourites stay with the user that made them.

## The checks

```bash
# how many items are in the table
aws dynamodb scan --table-name vibe --region ap-south-1 --select COUNT

# the files of a song
aws s3 ls s3://vibestack-mediabucketbcbb02ba-mgtm5ennm3bo/songs/ --recursive --region ap-south-1
```

Then sign in with google in the app and see the old songs, the old playlists
and the old favourites.

## The old project

When everything is checked, the old api can be shut down and the Supabase
project can be closed. Until then the `keepalive` script keeps it awake:

```bash
python scripts/keepalive_supabase.py
```

The github action in `.github/workflows/supabase-keepalive.yml` does the same
every three days.
