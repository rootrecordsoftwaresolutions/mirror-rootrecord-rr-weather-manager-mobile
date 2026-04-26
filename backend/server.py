"""Root Record Weather Manager — Mobile API.

Auth is validated via the single Cloudflare Worker `rootrecord-primary` (POST /api/auth/*).
Per-user saved locations use MongoDB; weather + hazard feeds are aggregated from public APIs.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import math
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from push_fcm import is_fcm_configured, send_multicast_blocking

load_dotenv()

# --------------------------------------------------------------------------- env
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
# Same origin as the mobile Worker API (no separate auth Worker).
PRIMARY_API_BASE = (
    os.environ.get("WEATHER_API_PUBLIC_URL")
    or os.environ.get("ROOTRECORD_PRIMARY_API")
    or "https://rootrecord-primary.rootrecord.workers.dev"
).rstrip("/")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

logger = logging.getLogger("rrweather")
logging.basicConfig(level=logging.INFO)

# --------------------------------------------------------------------------- db
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
locations_col = db["locations"]
guest_state_col = db["guest_state"]
device_locations_col = db["device_locations"]
push_tokens_col = db["push_tokens"]
# Isolated store for dashboard bundles: append-only rows for history + reuse within TTL.
weather_data_col = db["weather_data"]

WEATHER_DATA_TTL_SEC = int(os.environ.get("WEATHER_DATA_TTL_SEC", os.environ.get("WEATHER_CACHE_TTL_SEC", "600")))

# --------------------------------------------------------------------------- app
app = FastAPI(title="Root Record Weather Manager API", version="1.0.0")
api = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS.split(",")] if CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USER_AGENT = "RootRecordWeatherManagerMobile/1.0 (contact: root@rootrecord.info)"


# ============================================================================
#                                  MODELS
# ============================================================================
class Location(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    latitude: float
    longitude: float
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LocationCreate(BaseModel):
    name: str
    latitude: float
    longitude: float


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DeviceLocationReport(BaseModel):
    """Latest device GPS as reported by the client (e.g. on app open). Not a saved named location."""

    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None


class PushTokenRegister(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)
    platform: str = Field(default="android", max_length=32)


class PushBroadcastBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    body: str = Field(..., min_length=1, max_length=500)


class AuthCredentials(BaseModel):
    email: str
    password: str
    device_id: Optional[str] = None


class AuthResponse(BaseModel):
    ok: bool
    token: Optional[str] = None
    email: Optional[str] = None
    account_id: Optional[str] = None
    message: Optional[str] = None
    pro_unlocked: Optional[bool] = None


# ============================================================================
#                                  HELPERS
# ============================================================================
async def get_user_id(
    authorization: Optional[str] = Header(None),
    x_guest_id: Optional[str] = Header(None),
) -> str:
    """Resolve the caller: Bearer token validated against rootrecord-primary /api/auth/me, or guest."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        async with httpx.AsyncClient(timeout=12.0) as hc:
            try:
                r = await hc.post(
                    f"{PRIMARY_API_BASE}/api/auth/me",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={},
                )
                if r.status_code == 200:
                    data = r.json()
                    email = (data.get("email") or "").strip().lower()
                    if email and data.get("authenticated"):
                        return f"user:{email}"
            except Exception as e:  # noqa: BLE001
                logger.warning("auth/me validation failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    if x_guest_id:
        gid = re.sub(r"[^a-zA-Z0-9_-]", "", x_guest_id)[:64]
        if gid:
            return f"guest:{gid}"
    raise HTTPException(status_code=401, detail="Sign in or provide a guest id.")


async def require_push_broadcast_admin(
    x_rr_push_admin_key: Optional[str] = Header(None, description="Must match server RR_PUSH_ADMIN_SECRET"),
) -> None:
    """Protects POST /api/internal/push-broadcast (dev / ops only)."""
    secret = (os.environ.get("RR_PUSH_ADMIN_SECRET") or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="RR_PUSH_ADMIN_SECRET is not set on the server.")
    if not x_rr_push_admin_key:
        raise HTTPException(status_code=401, detail="Missing X-RR-Push-Admin-Key header.")
    p_hash = hashlib.sha256(x_rr_push_admin_key.encode("utf-8")).digest()
    s_hash = hashlib.sha256(secret.encode("utf-8")).digest()
    if not hmac.compare_digest(p_hash, s_hash):
        raise HTTPException(status_code=401, detail="Invalid admin key.")


def _doc_out(doc: dict) -> dict:
    """Strip MongoDB _id and return a plain dict."""
    if not doc:
        return doc
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


def haversine_miles(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    r = 3958.7613
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dphi = math.radians(b_lat - a_lat)
    dlmb = math.radians(b_lon - a_lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


# ============================================================================
#                                   ROOT
# ============================================================================
@api.get("/")
async def root():
    return {"name": "Root Record Weather Manager API", "version": "1.0.0"}


@api.get("/health")
async def health():
    try:
        await db.command("ping")
        return {"status": "ok", "db": "ok"}
    except Exception as e:  # noqa: BLE001
        return {"status": "degraded", "db": str(e)}


# ============================================================================
#                                   AUTH (proxy → rootrecord-primary /api/auth/*)
# ============================================================================
def _license_error_detail(data: object, status: int) -> str:
    msg = ""
    if isinstance(data, dict):
        msg = (data.get("detail") if isinstance(data.get("detail"), str) else "") or ""
        if not msg:
            msg = data.get("message") or (data.get("error") if isinstance(data.get("error"), str) else "")
        if not msg and isinstance(data.get("error"), dict):
            msg = data["error"].get("message") or ""
    return msg or f"Auth failed (HTTP {status})"


async def _proxy_primary_auth(path: str, payload: dict, token: Optional[str] = None) -> dict:
    """POST {PRIMARY_API_BASE}/api/auth/..."""
    async with httpx.AsyncClient(timeout=15.0) as hc:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            r = await hc.post(f"{PRIMARY_API_BASE}/api{path}", headers=headers, json=payload)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Auth service unreachable: {e}") from e
        try:
            data = r.json()
        except Exception:  # noqa: BLE001
            data = {}
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=_license_error_detail(data, r.status_code))
        return data if isinstance(data, dict) else {}


@api.post("/auth/login", response_model=AuthResponse)
async def auth_login(creds: AuthCredentials):
    payload: dict = {"email": creds.email, "password": creds.password}
    did = (creds.device_id or "").strip()
    if did:
        payload["device_id"] = did
    data = await _proxy_primary_auth("/auth/login", payload)
    token = data.get("access_token") or data.get("token")
    return AuthResponse(
        ok=True,
        token=token,
        email=(data.get("email") or creds.email).strip(),
        account_id=str(data.get("account_id") or ""),
        message=data.get("message") or "Signed in.",
        pro_unlocked=bool(data.get("proUnlocked") or data.get("pro_unlocked")),
    )


@api.post("/auth/signup", response_model=AuthResponse)
async def auth_signup(creds: AuthCredentials):
    payload: dict = {"email": creds.email, "password": creds.password}
    did = (creds.device_id or "").strip()
    if did:
        payload["device_id"] = did
    data = await _proxy_primary_auth("/auth/signup", payload)
    token = data.get("access_token") or data.get("token")
    return AuthResponse(
        ok=True,
        token=token,
        email=(data.get("email") or creds.email).strip(),
        account_id=str(data.get("account_id") or ""),
        message=data.get("message") or "Account created.",
        pro_unlocked=bool(data.get("proUnlocked") or data.get("pro_unlocked")),
    )


@api.post("/auth/me")
async def auth_me(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1].strip()
    async with httpx.AsyncClient(timeout=15.0) as hc:
        r = await hc.post(
            f"{PRIMARY_API_BASE}/api/auth/me",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={},
        )
        try:
            data = r.json()
        except Exception:  # noqa: BLE001
            data = {}
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=_license_error_detail(data, r.status_code))
    return {
        "authenticated": bool(data.get("authenticated")),
        "email": (data.get("email") or "").strip(),
        "pro_unlocked": bool(data.get("proUnlocked") or data.get("pro_unlocked")),
        "trial_ends_at": data.get("trialEndsAt"),
        "access": data.get("access"),
        "raw": data,
    }


# ============================================================================
#                                 LOCATIONS
# ============================================================================
@api.get("/locations", response_model=List[Location])
async def list_locations(user_id: str = Depends(get_user_id)):
    cursor = locations_col.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1)
    return [Location(**d) async for d in cursor]


@api.post("/locations", response_model=Location)
async def create_location(payload: LocationCreate, user_id: str = Depends(get_user_id)):
    if not payload.name.strip():
        raise HTTPException(400, "Location name is required.")
    if not (-90 <= payload.latitude <= 90) or not (-180 <= payload.longitude <= 180):
        raise HTTPException(400, "Latitude/longitude out of range.")
    loc = Location(user_id=user_id, name=payload.name.strip(),
                   latitude=payload.latitude, longitude=payload.longitude)
    await locations_col.insert_one(loc.model_dump())
    return loc


@api.patch("/locations/{location_id}", response_model=Location)
async def update_location(location_id: str, payload: LocationUpdate, user_id: str = Depends(get_user_id)):
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(400, "No fields to update.")
    await locations_col.update_one({"id": location_id, "user_id": user_id}, {"$set": update})
    doc = await locations_col.find_one({"id": location_id, "user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Location not found.")
    return Location(**doc)


@api.delete("/locations/{location_id}")
async def delete_location(location_id: str, user_id: str = Depends(get_user_id)):
    res = await locations_col.delete_one({"id": location_id, "user_id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Location not found.")
    return {"ok": True}


# ============================================================================
#                         DEVICE LOCATION (last known GPS)
# ============================================================================
@api.post("/me/device-location")
async def report_device_location(payload: DeviceLocationReport, user_id: str = Depends(get_user_id)):
    """Upsert the caller's most recent coordinates (privacy: same auth as saved locations)."""
    if not (-90 <= payload.latitude <= 90) or not (-180 <= payload.longitude <= 180):
        raise HTTPException(400, "Latitude/longitude out of range.")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "user_id": user_id,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "accuracy_m": payload.accuracy_m,
        "updated_at": now,
    }
    await device_locations_col.update_one({"user_id": user_id}, {"$set": doc}, upsert=True)
    return {"ok": True, "updated_at": now}


# ============================================================================
#                    PUSH TOKENS + DEV BROADCAST (FCM)
# ============================================================================
@api.post("/me/push-token")
async def register_push_token(payload: PushTokenRegister, user_id: str = Depends(get_user_id)):
    """Store FCM registration token for this user/guest (native app only)."""
    tok = payload.token.strip()
    if len(tok) < 20:
        raise HTTPException(status_code=400, detail="Invalid token.")
    plat = (payload.platform or "android").strip().lower()[:32]
    now = datetime.now(timezone.utc).isoformat()
    await push_tokens_col.update_one(
        {"token": tok},
        {"$set": {"user_id": user_id, "token": tok, "platform": plat, "updated_at": now}},
        upsert=True,
    )
    return {"ok": True}


@api.post("/internal/push-broadcast")
async def internal_push_broadcast(
    payload: PushBroadcastBody,
    _authorized: None = Depends(require_push_broadcast_admin),
):
    """Send a notification to every registered FCM token (test / ops). Requires X-RR-Push-Admin-Key."""
    if not is_fcm_configured():
        raise HTTPException(
            status_code=503,
            detail="FCM not configured. Set FCM_SERVICE_ACCOUNT_JSON to the path of your Firebase service account JSON file.",
        )
    seen: set[str] = set()
    tokens: List[str] = []
    async for doc in push_tokens_col.find({}, {"_id": 0, "token": 1}):
        t = (doc.get("token") or "").strip()
        if t and t not in seen:
            seen.add(t)
            tokens.append(t)
    if not tokens:
        return {
            "ok": True,
            "message": "No push tokens registered yet. Open the app on a device with FCM configured.",
            "fcm": {"success": 0, "failure": 0, "total_tokens": 0, "errors": []},
        }
    result = await asyncio.to_thread(send_multicast_blocking, tokens, payload.title, payload.body)
    logger.info("push-broadcast fcm result: %s", result)
    return {"ok": True, "fcm": result}


# ============================================================================
#                              WEATHER (NOAA NWS)
# ============================================================================
async def _nws_fetch(client_: httpx.AsyncClient, url: str) -> dict:
    r = await client_.get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"})
    if r.status_code >= 400:
        raise HTTPException(502, f"NWS upstream error: HTTP {r.status_code}")
    return r.json()


def _nws_quant_value(node: Any) -> Optional[float]:
    """NWS GeoJSON often uses { unitCode, value } quantitative nodes; value may be null."""
    if node is None:
        return None
    if isinstance(node, (int, float)):
        if isinstance(node, float) and (math.isnan(node) or math.isinf(node)):
            return None
        return float(node)
    if isinstance(node, dict):
        v = node.get("value")
        if v is None:
            return None
        try:
            out = float(v)
        except (TypeError, ValueError):
            return None
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    return None


def _observation_metric_score(props: dict) -> int:
    """How many primary 'now' metrics the station observation provides."""
    keys = ("temperature", "relativeHumidity", "windSpeed", "barometricPressure")
    return sum(1 for k in keys if _nws_quant_value((props or {}).get(k)) is not None)


def _parse_hourly_wind_speed_to_kmh(raw: Any) -> Optional[float]:
    """Hourly gridpoint forecast exposes windSpeed as a string like '7 mph' or '15 km/h'."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        try:
            n = float(raw)
        except (TypeError, ValueError):
            return None
        if math.isnan(n) or math.isinf(n):
            return None
        return n
    text = str(raw).strip().lower()
    if not text:
        return None
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if not nums:
        return None
    n = max(nums)
    if "km/h" in text or "kmh" in text:
        return n
    if "knot" in text or " kt" in text or text.endswith("kt"):
        return n * 1.852
    if "m/s" in text or "mps" in text:
        return n * 3.6
    if "mph" in text:
        return n * 1.60934
    # NWS US hourly is typically mph even when the token is omitted
    return n * 1.60934


def _merge_hourly_into_observation(observation: dict, hourly: dict) -> dict:
    """Fill missing station metrics from the first hourly period (different field shapes)."""
    out = dict(observation or {})
    if not hourly:
        return out
    if _nws_quant_value(out.get("relativeHumidity")) is None:
        rh = hourly.get("relativeHumidity")
        if isinstance(rh, dict) and rh.get("value") is not None:
            out["relativeHumidity"] = {
                "unitCode": rh.get("unitCode") or "wmoUnit:percent",
                "value": float(rh["value"]),
            }
    if _nws_quant_value(out.get("windSpeed")) is None:
        kmh = _parse_hourly_wind_speed_to_kmh(hourly.get("windSpeed"))
        if kmh is not None:
            out["windSpeed"] = {"unitCode": "wmoUnit:km_h-1", "value": kmh}
    if _nws_quant_value(out.get("windDirection")) is None:
        wd = hourly.get("windDirection")
        if isinstance(wd, str) and wd.strip():
            out["windDirectionCardinal"] = wd.strip()
    if _nws_quant_value(out.get("temperature")) is None and hourly.get("temperature") is not None:
        try:
            t = float(hourly["temperature"])
        except (TypeError, ValueError):
            t = None
        if t is not None:
            unit = str(hourly.get("temperatureUnit") or "").strip().upper()
            if unit not in ("F", "C"):
                unit = "F"
            if unit == "F":
                t = (t - 32.0) * 5.0 / 9.0
            out["temperature"] = {"unitCode": "wmoUnit:degC", "value": t}
    return out


async def _best_observation_from_stations(
    hc: httpx.AsyncClient, features: List[dict], max_stations: int = 8
) -> dict:
    """Try several nearby stations; NWS lists them in rough priority order."""
    best: dict = {}
    best_score = -1
    for feat in (features or [])[:max_stations]:
        sid = (feat.get("properties") or {}).get("stationIdentifier")
        if not sid:
            continue
        try:
            obs = await _nws_fetch(hc, f"https://api.weather.gov/stations/{sid}/observations/latest")
            props = (obs or {}).get("properties") or {}
            score = _observation_metric_score(props)
            if score > best_score:
                best_score = score
                best = props
            if score >= 4:
                break
        except Exception as e:  # noqa: BLE001
            logger.info("station %s observation failed: %s", sid, e)
            continue
    return best


def _weather_grid_key(lat: float, lon: float) -> str:
    return f"{round(lat, 3)},{round(lon, 3)}"


def _iso_age_seconds(iso_ts: Optional[str]) -> Optional[float]:
    if not iso_ts or not isinstance(iso_ts, str):
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds()


@api.get("/weather/current")
async def weather_current(lat: float = Query(...), lon: float = Query(...)):
    """Return current observation + a derived 'now' summary using the closest NWS station.
    Falls back to a 'forecastHourly' first period if observations are unavailable.
    """
    async with httpx.AsyncClient(timeout=15.0) as hc:
        try:
            points = await _nws_fetch(hc, f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}")
        except HTTPException:
            return {"available": False, "reason": "nws_points_unavailable"}
        props = (points or {}).get("properties") or {}
        stations_url = props.get("observationStations")
        forecast_url = props.get("forecast")
        forecast_hourly_url = props.get("forecastHourly")

        observation: dict = {}
        if stations_url:
            try:
                stations = await _nws_fetch(hc, stations_url)
                features = (stations or {}).get("features") or []
                if features:
                    observation = await _best_observation_from_stations(hc, features)
            except Exception as e:  # noqa: BLE001
                logger.info("station list/obs failed: %s", e)

        hourly_first: dict = {}
        if forecast_hourly_url:
            try:
                hourly = await _nws_fetch(hc, forecast_hourly_url)
                periods = ((hourly or {}).get("properties") or {}).get("periods") or []
                if periods:
                    hourly_first = periods[0]
            except Exception as e:  # noqa: BLE001
                logger.info("hourly fetch failed: %s", e)

        observation = _merge_hourly_into_observation(observation, hourly_first)

    return {
        "available": True,
        "observation": observation,
        "hourly_now": hourly_first,
        "forecast_url": forecast_url,
        "forecast_hourly_url": forecast_hourly_url,
        "city": props.get("relativeLocation", {}).get("properties", {}).get("city"),
        "state": props.get("relativeLocation", {}).get("properties", {}).get("state"),
    }


@api.get("/weather/forecast")
async def weather_forecast(lat: float = Query(...), lon: float = Query(...)):
    async with httpx.AsyncClient(timeout=15.0) as hc:
        try:
            points = await _nws_fetch(hc, f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}")
        except HTTPException:
            return {"available": False, "periods": [], "hourly": [], "hourly_grid_units": "us"}
        props = (points or {}).get("properties") or {}
        forecast_url = props.get("forecast")
        forecast_hourly_url = props.get("forecastHourly")

        periods: list = []
        hourly: list = []
        hourly_grid_units = "us"
        if forecast_url:
            try:
                fc = await _nws_fetch(hc, forecast_url)
                periods = ((fc or {}).get("properties") or {}).get("periods") or []
            except Exception as e:  # noqa: BLE001
                logger.info("forecast failed: %s", e)
        if forecast_hourly_url:
            try:
                fh = await _nws_fetch(hc, forecast_hourly_url)
                fh_props = (fh or {}).get("properties") or {}
                hourly = fh_props.get("periods") or []
                hourly = hourly[:24]
                hourly_grid_units = str(fh_props.get("units") or "us")
            except Exception as e:  # noqa: BLE001
                logger.info("hourly forecast failed: %s", e)

    return {"available": True, "periods": periods, "hourly": hourly, "hourly_grid_units": hourly_grid_units}


@api.get("/weather/alerts")
async def weather_alerts(lat: float = Query(...), lon: float = Query(...)):
    async with httpx.AsyncClient(timeout=15.0) as hc:
        try:
            r = await hc.get(
                f"https://api.weather.gov/alerts/active?point={lat:.4f},{lon:.4f}",
                headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
            )
            if r.status_code >= 400:
                return {"available": False, "alerts": []}
            data = r.json()
        except Exception as e:  # noqa: BLE001
            logger.info("noaa alerts failed: %s", e)
            return {"available": False, "alerts": []}
    features = (data or {}).get("features") or []
    out = []
    for f in features:
        p = f.get("properties") or {}
        out.append({
            "id": f.get("id"),
            "event": p.get("event"),
            "headline": p.get("headline"),
            "description": p.get("description"),
            "instruction": p.get("instruction"),
            "severity": p.get("severity"),
            "urgency": p.get("urgency"),
            "certainty": p.get("certainty"),
            "areaDesc": p.get("areaDesc"),
            "sent": p.get("sent"),
            "effective": p.get("effective"),
            "ends": p.get("ends") or p.get("expires"),
            "senderName": p.get("senderName"),
        })
    return {"available": True, "alerts": out}


# ============================================================================
#                               CANADA ALERTS
# ============================================================================
@api.get("/canada/alerts")
async def canada_alerts(lat: float = Query(...), lon: float = Query(...), radius_km: float = Query(150)):
    """Pulls Canadian Meteorological Service active alerts via the public GeoMet WMS GetFeature
    around the requested point. Returns [] outside Canada or when the feed is unavailable.
    """
    bbox_lon = radius_km / 80.0  # rough degrees
    bbox_lat = radius_km / 110.0
    bbox = f"{lon - bbox_lon},{lat - bbox_lat},{lon + bbox_lon},{lat + bbox_lat}"
    url = (
        "https://geo.weather.gc.ca/geomet/features/collections/ALERTS/items?"
        f"f=json&bbox={bbox}&limit=50"
    )
    async with httpx.AsyncClient(timeout=15.0) as hc:
        try:
            r = await hc.get(url, headers={"User-Agent": USER_AGENT})
            if r.status_code >= 400:
                return {"available": False, "alerts": []}
            data = r.json()
        except Exception as e:  # noqa: BLE001
            logger.info("canada alerts failed: %s", e)
            return {"available": False, "alerts": []}
    feats = (data or {}).get("features") or []
    out = []
    for f in feats:
        p = f.get("properties") or {}
        out.append({
            "id": f.get("id") or p.get("identifier"),
            "event": p.get("headline") or p.get("alert_type"),
            "headline": p.get("headline"),
            "description": p.get("descrip_en") or p.get("description"),
            "severity": p.get("severity"),
            "urgency": p.get("urgency"),
            "areaDesc": p.get("area") or p.get("location"),
            "sent": p.get("sent") or p.get("effective"),
            "effective": p.get("effective"),
            "ends": p.get("expires"),
        })
    return {"available": True, "alerts": out}


# ============================================================================
#                                 USGS
# ============================================================================
@api.get("/usgs/earthquakes")
async def usgs_earthquakes(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_miles: float = Query(2000.0),
    period: str = Query("day", regex="^(hour|day|week|month)$"),
    min_magnitude: float = Query(0.0),
):
    feed_map = {
        "hour": "all_hour",
        "day": "all_day",
        "week": "all_week",
        "month": "all_month",
    }
    feed = feed_map.get(period, "all_day")
    url = f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{feed}.geojson"
    async with httpx.AsyncClient(timeout=15.0) as hc:
        try:
            r = await hc.get(url, headers={"User-Agent": USER_AGENT})
            if r.status_code >= 400:
                return {"available": False, "events": []}
            data = r.json()
        except Exception as e:  # noqa: BLE001
            logger.info("usgs failed: %s", e)
            return {"available": False, "events": []}
    feats = (data or {}).get("features") or []
    out = []
    for f in feats:
        p = f.get("properties") or {}
        coords = (f.get("geometry") or {}).get("coordinates") or [None, None, None]
        e_lon, e_lat, e_depth = coords[0], coords[1], coords[2] if len(coords) > 2 else None
        mag = p.get("mag")
        if mag is None or mag < min_magnitude:
            continue
        distance = None
        if lat is not None and lon is not None and e_lat is not None and e_lon is not None:
            distance = haversine_miles(lat, lon, e_lat, e_lon)
            if distance > radius_miles:
                continue
        out.append({
            "id": f.get("id"),
            "magnitude": mag,
            "place": p.get("place"),
            "time": p.get("time"),
            "updated": p.get("updated"),
            "url": p.get("url"),
            "tsunami": bool(p.get("tsunami")),
            "alert": p.get("alert"),
            "depth_km": e_depth,
            "lat": e_lat,
            "lon": e_lon,
            "distance_miles": distance,
        })
    out.sort(key=lambda x: x.get("time") or 0, reverse=True)
    return {"available": True, "events": out}


@api.get("/usgs/tsunamis")
async def tsunami_bulletins():
    """Pull recent significant earthquakes flagged with tsunami=1 plus the PTWC bulletin
    title list via USGS feed.
    """
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"
    async with httpx.AsyncClient(timeout=15.0) as hc:
        try:
            r = await hc.get(url, headers={"User-Agent": USER_AGENT})
            if r.status_code >= 400:
                return {"available": False, "bulletins": []}
            data = r.json()
        except Exception as e:  # noqa: BLE001
            logger.info("ptwc fetch failed: %s", e)
            return {"available": False, "bulletins": []}
    out = []
    for f in (data or {}).get("features") or []:
        p = f.get("properties") or {}
        if not p.get("tsunami"):
            continue
        out.append({
            "id": f.get("id"),
            "title": p.get("title"),
            "place": p.get("place"),
            "magnitude": p.get("mag"),
            "time": p.get("time"),
            "url": p.get("url"),
            "alert": p.get("alert"),
        })
    return {"available": True, "bulletins": out}


# ============================================================================
#                              NASA EONET
# ============================================================================
async def _eonet_events(category: str, days: int = 30) -> list:
    url = f"https://eonet.gsfc.nasa.gov/api/v3/events?category={category}&status=open&days={days}"
    async with httpx.AsyncClient(timeout=15.0) as hc:
        try:
            r = await hc.get(url, headers={"User-Agent": USER_AGENT})
            if r.status_code >= 400:
                return []
            data = r.json()
        except Exception as e:  # noqa: BLE001
            logger.info("eonet %s failed: %s", category, e)
            return []
    out = []
    for ev in (data or {}).get("events") or []:
        geoms = ev.get("geometry") or []
        last = geoms[-1] if geoms else {}
        coords = last.get("coordinates") or [None, None]
        out.append({
            "id": ev.get("id"),
            "title": ev.get("title"),
            "description": ev.get("description"),
            "categories": [c.get("title") for c in ev.get("categories") or []],
            "sources": [s.get("url") for s in ev.get("sources") or []],
            "lat": coords[1] if len(coords) > 1 else None,
            "lon": coords[0] if coords else None,
            "date": last.get("date"),
            "magnitudeValue": last.get("magnitudeValue"),
            "magnitudeUnit": last.get("magnitudeUnit"),
        })
    return out


@api.get("/eonet/cyclones")
async def eonet_cyclones():
    return {"available": True, "events": await _eonet_events("severeStorms", 30)}


@api.get("/eonet/wildfires")
async def eonet_wildfires():
    return {"available": True, "events": await _eonet_events("wildfires", 30)}


# ============================================================================
#                              DASHBOARD BUNDLE
# ============================================================================
@api.get("/dashboard")
async def dashboard(
    lat: float = Query(...),
    lon: float = Query(...),
    refresh: bool = Query(False, description="If true, bypass cache and refresh upstream data."),
    location_id: Optional[str] = Query(
        None,
        max_length=64,
        description="Saved location id from the app; stored with each snapshot for history.",
    ),
    user_id: str = Depends(get_user_id),
):
    """One-shot bundle for mobile home: current weather, NOAA alerts, nearby USGS, and
    the next 12 hourly periods. Each is best-effort; failures degrade gracefully.

    Latest row per user + grid in ``weather_data`` reused within WEATHER_DATA_TTL_SEC;
    each upstream fetch appends a new row (historical record). Pass refresh=1 to force fetch.
    """
    grid_key = _weather_grid_key(lat, lon)
    if not refresh:
        try:
            cur = (
                weather_data_col.find({"user_id": user_id, "grid_key": grid_key}, {"_id": 0, "bundle": 1, "fetched_at": 1})
                .sort("fetched_at", -1)
                .limit(1)
            )
            cached_rows = await cur.to_list(length=1)
            cached = cached_rows[0] if cached_rows else None
        except Exception as e:  # noqa: BLE001
            logger.warning("weather_data read failed: %s", e)
            cached = None
        if cached and isinstance(cached.get("bundle"), dict):
            age = _iso_age_seconds(cached.get("fetched_at"))
            if age is not None and age < WEATHER_DATA_TTL_SEC:
                return cached["bundle"]

    current_t = weather_current(lat=lat, lon=lon)
    alerts_t = weather_alerts(lat=lat, lon=lon)
    canada_t = canada_alerts(lat=lat, lon=lon)
    usgs_t = usgs_earthquakes(lat=lat, lon=lon, radius_miles=300, period="day", min_magnitude=2.5)
    forecast_t = weather_forecast(lat=lat, lon=lon)

    current, alerts, canada, usgs, forecast = await asyncio.gather(
        current_t, alerts_t, canada_t, usgs_t, forecast_t, return_exceptions=True
    )

    def safe(v, default):
        if isinstance(v, Exception):
            return default
        return v

    bundle = {
        "current": safe(current, {"available": False}),
        "alerts": safe(alerts, {"available": False, "alerts": []}),
        "canada_alerts": safe(canada, {"available": False, "alerts": []}),
        "usgs": safe(usgs, {"available": False, "events": []}),
        "forecast": safe(forecast, {"available": False, "periods": [], "hourly": []}),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    fetched_at = bundle["fetched_at"]
    doc = {
        "user_id": user_id,
        "location_id": (location_id.strip() or None) if location_id else None,
        "grid_key": grid_key,
        "latitude": lat,
        "longitude": lon,
        "fetched_at": fetched_at,
        "bundle": bundle,
    }
    try:
        await weather_data_col.insert_one(doc)
    except Exception as e:  # noqa: BLE001
        logger.warning("weather_data insert failed: %s", e)
    return bundle


app.include_router(api)


@app.on_event("startup")
async def on_startup():
    await locations_col.create_index([("user_id", 1)])
    await locations_col.create_index([("user_id", 1), ("id", 1)], unique=True)
    await device_locations_col.create_index([("user_id", 1)], unique=True)
    await push_tokens_col.create_index([("token", 1)], unique=True)
    await weather_data_col.create_index([("user_id", 1), ("grid_key", 1), ("fetched_at", -1)])
    await weather_data_col.create_index([("user_id", 1), ("location_id", 1), ("fetched_at", -1)])
    logger.info("Root Record Weather Manager API ready.")
