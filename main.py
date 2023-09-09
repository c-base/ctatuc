import json
from typing import Annotated
from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.config import Config
from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.middleware.sessions import SessionMiddleware
# from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.responses import HTMLResponse, RedirectResponse


class Settings(BaseSettings):
    client_id: str
    client_secret: str

    # File '.env' will be read
    model_config = SettingsConfigDict(env_file=".env")
settings = Settings()

config = Config('.oauth_env')  # read config from .env file

oauth = OAuth(config)

# print(f"client_id: {config.get('client_id', None)}")
oauth.register(
    name='cbase',
    server_metadata_url='https://c-base.org/oauth/.well-known/openid-configuration/',
    client_id=settings.client_id,
    client_secret=settings.client_secret,
    client_kwargs={
        'scope': 'openid',
    }
)

app = FastAPI()
# oauth2_scheme = OAuth2AuthorizationCodeBearer(scopes={"openid": "openid"}, authorizationUrl="https://c-base.org/oauth/authorize/", tokenUrl="https://c-base.org/oauth/token/")
app.add_middleware(SessionMiddleware, secret_key="secret-string")
templates = Jinja2Templates(directory="templates")
# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get('/')
async def homepage(request: Request):
    user = request.session.get('user')
    if user:
        context = {
            "data": json.dumps(user),
            "user": user,
            "request": request
        }
        return templates.TemplateResponse("index.html", context)
    return templates.TemplateResponse("index_login_required.html", {"request": request})

@app.get('/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/')


@app.route('/login')
async def login(request: Request):
    user = request.session.get('user')
    if user:
        return RedirectResponse(url='/')
    # absolute url for callback
    # we will define it below
    redirect_uri = request.url_for('auth')
    print(redirect_uri)
    return await oauth.cbase.authorize_redirect(request, redirect_uri)


@app.route('/auth')
async def auth(request: Request):
    token = await oauth.cbase.authorize_access_token(request)
    user = token.get('userinfo')
    if user:
        request.session['user'] = dict(user)
    return RedirectResponse(url='/')



# @app.get("/items/")
#async def read_items(token: Annotated[str, Depends(oauth)]):
#    return {"token": token}
