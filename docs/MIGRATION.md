# Moving the data from the old database and Cloudinary to AWS

The app now lives on AWS: the songs and the users are in DynamoDB, the song files
are in S3, and the api runs on Lambda behind CloudFront. This page is the
step by step plan to move the data of the old project over.

Nothing in the old project is deleted by these steps, so the old api keeps
working until the new one is checked.

## What is moved where

| old | new |
| --- | --- |
| the `users` table of the old postgres database | the `USER#<id>` items in the `vibe` table |
| the `songs`, `playlists`, `playlist_songs` and `favourites` tables | the `SONG#<id>`, `PLAYLIST#<id>` and `IDX_` items in the same table |
| the song files in Cloudinary | the `songs/<song id>/` objects in the S3 bucket |
| the google login of Supabase | the google login of the app, the `google_sub` keeps the link |

The user id does not change, so the playlists and the favourites of every user
stay connected to their owner.

## Before you start

You need a `.env` file in the `server` folder with:

```
DATABASE_URL=postgresql+psycopg2://...the old postgres database...
AWS_REGION=ap-south-1
DYNAMODB_TABLE_NAME=vibe
S3_BUCKET=vibestack-mediabucketbcbb02ba-mgtm5ennm3bo
MEDIA_BASE_URL=https://d3hb9a4bci0gq5.cloudfront.net
```

The old database only listens on the machine it runs on, so a tunnel is opened
to it and the url points at the tunnel:

```bash
ssh -i <the key of the machine> -L 55432:127.0.0.1:5432 ubuntu@<the machine>
```

```bash
DATABASE_URL=postgresql://postgres:<the password>@127.0.0.1:55432/vibe
```

The aws keys come from the login session:

```bash
aws configure export-credentials --profile mudit-palvadi --format env
```

## Step 1: the song files

```bash
python scripts/copy_media_to_s3.py
```

Every audio file and every thumbnail is downloaded from Cloudinary and put into
the bucket under `songs/<song id>/`. The script writes `scripts/media_map.json`
with the new addresses of the files, the next script uses it.

## Step 2: the users

```bash
python scripts/migrate_users_to_dynamodb.py
```

## Step 3: the songs, the playlists and the favourites

```bash
python scripts/migrate_content_to_dynamodb.py
```

The songs get the new addresses of their files from the media map, the playlists
keep their songs, and the favourites stay with the user that made them.

## The google id of the users

The new api looks a user up by the id that google gives them. A user that was
moved without a google id is found by the email the first time they sign in,
and the api writes the google id down then. So nothing has to be done for the
move.

`scripts/migrate_google_sub.py` fills the column in the old database from the
`auth.identities` table of Supabase. It is only needed when the google id has
to be known before the first sign in.

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

When everything is checked, the old api and the old database can be shut down.
Supabase only held the google login, so it can be closed too. Until then the
`keepalive` script keeps it awake:

```bash
python scripts/keepalive_supabase.py
```

The github action in `.github/workflows/supabase-keepalive.yml` does the same
every three days.
