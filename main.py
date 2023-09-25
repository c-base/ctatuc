import asyncio
import json
import aiomqtt
from aiomqtt.error import MqttError
from typing import Annotated
from datetime import datetime
from authlib.integrations.starlette_client import OAuth, OAuthError
from contextlib import asynccontextmanager
from starlette.config import Config
from fastapi import Depends, FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import BackgroundTasks
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


templates = Jinja2Templates(directory="templates")
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

door_status = {
    "current": "unknown",
    "updated": None,
    "changes": []
}

MAX_CHANGES = 10
MQTT_TIMEOUT = 5

class MQTTRunner:
    def __init__(self):
        self.started = False

    async def mqtt_loop(self):
        global door_status
        try:
            async with aiomqtt.Client("10.0.1.17", timeout=MQTT_TIMEOUT) as client:
                async with client.messages() as messages:
                    await client.subscribe("sensor/c-leuse/status")
                    async for message in messages:
                        now = datetime.now()
                        payload = message.payload.decode()
                        door_status['updated'] = now
                        if door_status['current'] != payload:
                            door_status['changes'].append({
                                'from': door_status['current'],
                                'to': payload,
                                'when': now,
                            })
                            if len(door_status['changes']) > MAX_CHANGES:
                                door_status['changes'] = door_status['changes'][:-MAX_CHANGES]
                        door_status['current'] = payload
        except MqttError as error:
            door_status['changes'].append({
                'from': door_status['current'],
                'to': 'unknown',
                'when': datetime.now(),
            })
            door_status['updated'] = datetime.now()
            door_status['current'] = f"'ERROR: {error}'"
            await asyncio.sleep(2.0)

    async def run_main(self):
        self.started = True
        while self.started is True:
            await asyncio.sleep(0.1)
            await self.mqtt_loop()
                    
    async def stop(self):
        self.started = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    runner = MQTTRunner()
    loop = asyncio.get_event_loop()
    loop.create_task(runner.run_main())
    yield
    # Clean up the ML models and release the resources
    runner.stop()

app = FastAPI(lifespan=lifespan)

# oauth2_scheme = OAuth2AuthorizationCodeBearer(scopes={"openid": "openid"}, authorizationUrl="https://c-base.org/oauth/authorize/", tokenUrl="https://c-base.org/oauth/token/")
app.add_middleware(SessionMiddleware, secret_key="secret-string")


# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get('/')
async def homepage(request: Request):
    user = request.session.get('user')
    if user:
        context = {
            "data": json.dumps(user),
            "user": user,
            "request": request,
            "status": door_status,
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
