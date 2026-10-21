from mangum import Mangum

from app.main import app

# aws lambda calls this handler, mangum turns the lambda event into the
# asgi request that fastapi expects
handler = Mangum(app)
