# The Deployment Runbook

Everything below runs from the `server` folder. The backend is serverless, so
there is no server to keep alive, only the aws resources.

## What is where

| Piece | Where | Region |
| --- | --- | --- |
| the api (fastapi in a lambda) | `VibeStack` | ap-south-1 |
| the table (dynamodb) | `VibeStack` | ap-south-1 |
| the song files (s3) | `VibeStack` | ap-south-1 |
| the cdn (cloudfront) | `VibeStack` | global |
| the session secret | ssm parameter `/vibe/session-secret` | ap-south-1 |
| the google client id | ssm parameter `/vibe/google-client-id` | ap-south-1 |

Everything lives in ap-south-1. The web acl (waf) is not used while the
account is on the free plan, it costs about 5 dollars a month, see the free
plan section below.

## Before the first deploy

```powershell
# the aws cli, the account is free plan
aws login --profile mudit-palvadi

# the cdk cli is a global npm install
npm install -g aws-cdk

# aws cdk lib lives in the project venv, so the venv has to be on the path
pip install -r infra/cdk/requirements.txt
$env:PATH = "$PWD\venv\Scripts;$env:PATH"
```

The account uses a login session, so the credentials have to be exported before
every aws call, the cli and boto3 cannot read the session on their own:

```powershell
$lines = aws configure export-credentials --profile mudit-palvadi --format env
foreach ($l in $lines) {
    if ($l -match '^(?:export\s+)?([A-Z_]+)=(.*)$') {
        Set-Item -Path "Env:$($matches[1])" -Value $matches[2]
    }
}
```

The session is short, so export it again if a call starts to fail.

## The deploy

```powershell
# the code of the lambda, it has to be built before every deploy
python scripts/build_lambda_zip.py

# the toolkit, once per region
cdk bootstrap aws://257209856532/ap-south-1

# the stack itself
cdk deploy VibeStack --require-approval never
```

The distribution cannot know its own domain name while it is made, so the
media links are empty on the first deploy. The `app.py` of the cdk looks the
domain up in the stack outputs, so the second deploy fills it in:

```powershell
cdk deploy VibeStack --require-approval never
```

The google client id comes from the parameter store, so it is set once:

```powershell
aws ssm put-parameter --name /vibe/google-client-id --value "<the google client id>" --type String --overwrite
```

## The free cdn plan

The account is on the aws free plan, and the cloudfront flat rate plan is not
available there:

```
AWS Free Tier accounts can't create flat-rate pricing subscriptions.
Upgrade to a paid account plan and try again.
```

So the distribution is on the pay as you go price, where the first 1 tb of
transfer and 10 million requests a month are free, and the requests to the
aws origin are free as well. The web acl (waf) is not used, it costs about 5
dollars a month and would eat the credits of the account. The `EdgeStack` in
`infra/cdk/edge_stack.py` is kept in the repository and comes back when the
account is on the paid plan:

```powershell
# on the paid plan
cdk deploy EdgeStack --require-approval never
```

## The data move

The old data is still in supabase and cloudinary. The scripts do the move, they
read the old project and write the new one. They read the old database and the
old supabase project from the `.env` file of the server folder:

```powershell
# the old database, the connection string of the supabase project
# DATABASE_URL=postgresql://<user>:<password>@<host>:5432/postgres
# the old supabase project
# SUPABASE_URL=https://<project>.supabase.co
# SUPABASE_SERVICE_ROLE_KEY=<the service role key>

python scripts/migrate_google_sub.py            # once, adds the google id to the old database
python scripts/migrate_users_to_dynamodb.py     # the users, with their google ids
python scripts/copy_media_to_s3.py              # the song files, it writes scripts/media_map.json
python scripts/migrate_content_to_dynamodb.py   # the songs, the playlists and the favourites
```

## The checks

```powershell
# the local tests
python -m pytest

# the same tests against the real table
$env:RUN_DYNAMODB_TESTS = "1"
python -m pytest tests/test_dynamodb_contracts.py

# the live api
curl https://<the distribution domain>/
```

## The gotchas

- The cdk cli sets `CDK_DEFAULT_REGION` to the region of the first stack in
  the assembly, so `app.py` keeps its own regions and never reads that
  variable.
- The lambda zip is built for linux, the local venv has the windows wheels, so
  the build script downloads the linux ones.
- The aws cli and the cdk cli can hit a temporary network error, the command
  can just be run again.
