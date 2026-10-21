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
| the web acl (waf) | `EdgeStack` | us-east-1 |
| the session secret | ssm parameter `/vibe/session-secret` | ap-south-1 |

The web acl has to live in us-east-1 because a cloudfront web acl is a global
resource, everything else lives in ap-south-1.

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
cdk bootstrap aws://257209856532/us-east-1

# the web acl first, the distribution needs its arn
cdk deploy EdgeStack --require-approval never

# the rest, the web acl arn comes from the edge stack
cdk deploy VibeStack --require-approval never --context "wafAclArn=<the arn>"
```

The distribution cannot know its own domain name while it is made, so the
media links are empty on the first deploy. After the deploy the domain is in
the stack output, and the second deploy fills it in:

```powershell
cdk deploy VibeStack --require-approval never --context "wafAclArn=<the arn>" --context "mediaBaseUrl=https://<the distribution domain>"
```

The google client id is given the same way, with `--context "googleClientId=..."`.
It is the client id of the google desktop app credential, the same one the
flutter app uses.

## The free cdn plan

The cloudfront flat rate plan is what keeps the cdn free, one plan covers one
distribution and one web acl. It is done with the pricing plan manager, in
us-east-1, once the distribution exists:

```powershell
aws pricing-plan-manager create-subscription --plan-family CloudFront --plan-tier FREE --region us-east-1 --resource-arns <the distribution arn> <the web acl arn>
```

The free plan gives 1 million requests and 100 gb of transfer a month, there
are no overage charges, and the aws origin traffic is free.

## The data move

The old data is still in supabase and cloudinary. The scripts do the move, they
read the old project and write the new one:

```powershell
python scripts/migrate_users_to_dynamodb.py     # the users, with their google ids
python scripts/copy_media_to_s3.py              # the song files, it writes scripts/media_map.json
python scripts/migrate_content_to_dynamodb.py   # the songs, the playlists and the favourites
```

`scripts/migrate_google_sub.py` is only needed once, it adds the google id
column to the old database and fills it from the supabase accounts.

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
