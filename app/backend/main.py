"""
LocalizaVotos — Backend FastAPI
================================
Serve a API REST e os arquivos estáticos do frontend.

Variáveis de ambiente:
  SECRET_KEY           — chave de assinatura JWT (obrigatória em produção)
  ADMIN_PASSWORD_HASH  — SHA-256 da senha do admin
  ADMIN_EMAIL          — e-mail do admin para recuperação de senha
  SMTP_HOST            — ex: smtp.gmail.com
  SMTP_PORT            — padrão 587
  SMTP_USER            — remetente SMTP
  SMTP_PASSWORD        — senha / app-password SMTP
  APP_BASE_URL         — URL pública da aplicação (para links no e-mail)
  CANDIDATOS_DIR       — caminho da pasta candidatos (padrão: ../../candidatos)
  DATA_DIR             — caminho da pasta data (padrão: ../../data)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production-immediately")
ALGORITHM = "HS256"
TOKEN_HOURS = 24
RESET_MINUTES = 30

_HERE = Path(__file__).parent          # app/backend/
_APP = _HERE.parent                    # app/
_ROOT = _APP.parent                    # workspace root (localizavotos/)

CANDIDATOS_DIR = Path(os.getenv("CANDIDATOS_DIR", str(_ROOT / "candidatos")))
DATA_DIR = Path(os.getenv("DATA_DIR", str(_ROOT / "data")))
FRONTEND_DIR = _APP / "frontend"

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

# armazenamento em memória dos tokens de reset  {token: {slug, expires_at}}
_reset_store: dict[str, dict] = {}
_cache: dict[str, Any] = {}
_executor = ThreadPoolExecutor(max_workers=2)

# ---------------------------------------------------------------------------
# Ciclo de vida — pré-carrega arquivos pesados
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    ce_file = DATA_DIR / "ce_regioes.geojson"
    if ce_file.exists():
        try:
            _cache["ce_regioes"] = json.loads(ce_file.read_text(encoding="utf-8"))
            print(f"[startup] ce_regioes.geojson carregado ({ce_file.stat().st_size // 1024} KB)")
        except Exception as exc:
            print(f"[startup] Erro ao carregar ce_regioes.geojson: {exc}")
    yield
    _cache.clear()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="LocalizaVotos API", version="2.0.0", docs_url="/api/docs", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Normalização GeoJSON (portado de localiza/schema.py)
# ---------------------------------------------------------------------------

_ALIASES: dict[str, list[str]] = {
    "municipio": ["municipio", "município", "Municipio", "Município", "NM_MUNICIPIO", "NM_MUN"],
    "bairro": ["Bairro", "bairro", "Bairro/Distrito", "BAIRRO", "Distrito", "distrito", "bairro_distrito"],
    "local_votacao": ["local_votacao", "NM_LOCAL_VOTACAO", "local votação", "local", "LOCAL_VOT"],
    "qt_votos": ["qt_votos", "QT_VOTOS", "votos", "qtde_votos", "quantidade_votos"],
    "nome": ["nome", "Nome", "NM_LOCAL_VOTACAO", "NM_MUNICIPIO", "BAIRRO", "LABEL", "label", "LOCALIDADE"],
    "lat": ["lat", "LAT", "latitude", "Latitude"],
    "lon": ["lon", "LON", "longitude", "Longitude", "lng", "LNG"],
}


def _pick(props: dict, keys: list[str]) -> Any:
    for k in keys:
        if k in props:
            return props[k]
        for pk in props:
            if str(pk).lower() == k.lower():
                return props[pk]
    return None


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "")
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _get_latlon(props: dict, geom: dict) -> tuple[Optional[float], Optional[float]]:
    lat = _pick(props, _ALIASES["lat"])
    lon = _pick(props, _ALIASES["lon"])
    latn, lonn = _safe_float(lat), _safe_float(lon)
    if latn is not None and lonn is not None:
        return latn, lonn
    try:
        if (geom or {}).get("type") == "Point":
            c = (geom or {}).get("coordinates") or []
            if len(c) >= 2:
                return float(c[1]), float(c[0])
    except Exception:
        pass
    return None, None


def _normalize_points(gj: dict) -> dict:
    """Normaliza features Point para a resposta da API."""
    out = []
    for ft in (gj.get("features") or []):
        props = dict(ft.get("properties") or {})
        geom = ft.get("geometry") or {}
        lat, lon = _get_latlon(props, geom)
        if lat is None or lon is None:
            continue
        municipio = str(_pick(props, _ALIASES["municipio"]) or "")
        bairro = str(_pick(props, _ALIASES["bairro"]) or "")
        local = str(_pick(props, _ALIASES["local_votacao"]) or "")
        qt = _safe_float(_pick(props, _ALIASES["qt_votos"])) or 0.0
        nome = str(_pick(props, _ALIASES["nome"]) or local or municipio or "")
        props.update({
            "_municipio": municipio,
            "_bairro": bairro,
            "_local": local,
            "_qt_votos": qt,
            "_nome": nome,
        })
        out.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": out}


def _merge_municipios(votos_gj: dict) -> dict:
    """Funde votos por município com os polígonos de ce_regioes.geojson."""
    votes_by_mun: dict[str, float] = {}
    for ft in (votos_gj.get("features") or []):
        props = ft.get("properties") or {}
        mun = str(_pick(props, _ALIASES["municipio"]) or "").upper().strip()
        qt = _safe_float(_pick(props, _ALIASES["qt_votos"])) or 0.0
        if mun:
            votes_by_mun[mun] = votes_by_mun.get(mun, 0.0) + qt

    ce_gj = _cache.get("ce_regioes") or {}
    features_out = []
    for ft in (ce_gj.get("features") or []):
        props = dict(ft.get("properties") or {})
        mun_name = str(props.get("Municipio", "")).upper().strip()
        qt = votes_by_mun.get(mun_name, 0.0)
        props["_qt_votos"] = qt
        props["_municipio"] = props.get("Municipio", "")
        features_out.append({**ft, "properties": props})

    return {"type": "FeatureCollection", "features": features_out}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _verify_pwd(password: str, hash_: str) -> bool:
    return bool(hash_) and _sha256(password) == hash_


def _create_token(sub: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": sub, "role": role, "exp": exp}, SECRET_KEY, ALGORITHM)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _get_current(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido ou expirado")


# ---------------------------------------------------------------------------
# Candidato helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _get_creds(slug: str) -> Optional[dict]:
    if slug == ADMIN_USERNAME:
        return (
            {"display_name": "Admin", "email": ADMIN_EMAIL, "password_hash": ADMIN_PASSWORD_HASH}
            if ADMIN_PASSWORD_HASH
            else None
        )
    return _load_json(CANDIDATOS_DIR / slug / "credentials.json")


def _list_candidates() -> list[dict]:
    result = []
    if not CANDIDATOS_DIR.exists():
        return result
    for d in sorted(CANDIDATOS_DIR.iterdir()):
        if not d.is_dir():
            continue
        creds = _load_json(d / "credentials.json")
        if not creds:
            continue
        result.append({"slug": d.name, "display_name": creds.get("display_name", d.name)})
    return result


def _get_bases(slug: str) -> list[str]:
    folder = CANDIDATOS_DIR / slug
    if not folder.exists():
        return []
    return [f.stem[len("votos_"):] for f in sorted(folder.glob("votos_*.geojson"))]


def _find_slug_by_email(email: str) -> Optional[str]:
    email_lower = email.lower().strip()
    if CANDIDATOS_DIR.exists():
        for d in CANDIDATOS_DIR.iterdir():
            if not d.is_dir():
                continue
            creds = _load_json(d / "credentials.json")
            if creds and creds.get("email", "").lower() == email_lower:
                return d.name
    if ADMIN_EMAIL and ADMIN_EMAIL.lower() == email_lower:
        return ADMIN_USERNAME
    return None


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------

class LoginBody(BaseModel):
    username: str
    password: str


class ForgotBody(BaseModel):
    email: str


class ResetBody(BaseModel):
    token: str
    new_password: str


class CredentialsBody(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None


# ---------------------------------------------------------------------------
# Rotas — Autenticação
# ---------------------------------------------------------------------------

@app.post("/api/auth/login")
async def login(body: LoginBody):
    # Tenta slug direto; se não encontrar, tenta resolver por e-mail
    slug = body.username.strip()
    creds = _get_creds(slug)
    if not creds and "@" in slug:
        resolved = _find_slug_by_email(slug)
        if resolved:
            slug = resolved
            creds = _get_creds(slug)
    if not creds or not _verify_pwd(body.password, creds.get("password_hash", "")):
        raise HTTPException(401, "Usuário ou senha inválidos")
    role = "admin" if slug == ADMIN_USERNAME else "candidate"
    token = _create_token(slug, role)
    bases = _get_bases(slug) if role == "candidate" else []
    return {
        "access_token": token,
        "token_type": "bearer",
        "display_name": creds.get("display_name", slug),
        "slug": slug,
        "role": role,
        "bases": bases,
    }


@app.post("/api/auth/forgot-password")
async def forgot_password(body: ForgotBody):
    slug = _find_slug_by_email(body.email)
    if slug and SMTP_HOST and SMTP_USER:
        token = secrets.token_urlsafe(32)
        _reset_store[token] = {
            "slug": slug,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=RESET_MINUTES),
        }
        creds = _get_creds(slug)
        display_name = creds.get("display_name", slug) if creds else slug
        to_email = (creds.get("email", body.email) if creds else body.email)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            _executor, _send_reset_email, to_email, token, display_name
        )
    # Resposta genérica por segurança
    return {"message": "Se o e-mail estiver cadastrado, você receberá um link em breve."}


@app.post("/api/auth/reset-password")
async def reset_password(body: ResetBody):
    entry = _reset_store.get(body.token)
    if not entry:
        raise HTTPException(400, "Link inválido ou já utilizado.")
    if datetime.now(timezone.utc) > entry["expires_at"]:
        _reset_store.pop(body.token, None)
        raise HTTPException(400, "Link expirado. Solicite um novo.")
    slug = entry["slug"]
    if slug == ADMIN_USERNAME:
        raise HTTPException(400, "Reset de senha admin não é suportado por este meio.")
    cred_file = CANDIDATOS_DIR / slug / "credentials.json"
    if not cred_file.exists():
        raise HTTPException(500, "Credenciais não encontradas.")
    creds = json.loads(cred_file.read_text(encoding="utf-8"))
    creds["password_hash"] = _sha256(body.new_password)
    cred_file.write_text(json.dumps(creds, ensure_ascii=False, indent=2), encoding="utf-8")
    _reset_store.pop(body.token, None)
    return {"message": "Senha atualizada com sucesso."}


# ---------------------------------------------------------------------------
# Rotas — Candidatos
# ---------------------------------------------------------------------------

@app.get("/api/candidatos")
async def list_candidatos():
    return _list_candidates()


@app.get("/api/me")
async def me(payload: dict = Depends(_get_current)):
    slug = payload["sub"]
    role = payload.get("role", "candidate")
    creds = _get_creds(slug)
    bases = _get_bases(slug) if role == "candidate" else []
    return {
        "slug": slug,
        "role": role,
        "display_name": creds.get("display_name", slug) if creds else slug,
        "bases": bases,
    }


# ---------------------------------------------------------------------------
# Rotas — GeoJSON
# ---------------------------------------------------------------------------

@app.get("/api/candidato/votos/{base}")
async def get_votos(base: str, payload: dict = Depends(_get_current)):
    slug = payload["sub"]
    role = payload.get("role", "candidate")
    if role == "admin":
        raise HTTPException(400, "Admin deve usar /api/admin/candidato/{slug}/votos/{base}")

    votos_file = CANDIDATOS_DIR / slug / f"votos_{base}.geojson"
    if not votos_file.exists():
        raise HTTPException(404, f"Base de votos '{base}' não encontrada.")

    gj = _load_json(votos_file)
    if not gj:
        raise HTTPException(500, "Erro ao ler arquivo GeoJSON.")

    is_municipios = "municipio" in base.lower()
    if is_municipios and _cache.get("ce_regioes"):
        return _merge_municipios(gj)
    return _normalize_points(gj)


@app.get("/api/candidato/layers")
async def get_layers(payload: dict = Depends(_get_current)):
    slug = payload["sub"]
    role = payload.get("role", "candidate")
    if role == "admin":
        return []
    layers: list[dict] = []
    folder = CANDIDATOS_DIR / slug
    if folder.exists():
        for f in sorted(folder.glob("*.geojson")):
            if not f.stem.startswith("votos_"):
                layers.append({"source": "candidato", "name": f.stem, "label": f.stem.replace("_", " ").title()})
    if DATA_DIR.exists():
        for f in sorted(DATA_DIR.glob("*.geojson")):
            if f.stem not in ("ce_regioes",):
                layers.append({"source": "data", "name": f.stem, "label": f.stem.replace("_", " ").title()})
    return layers


@app.get("/api/candidato/layer/{source}/{name}")
async def get_layer(source: str, name: str, payload: dict = Depends(_get_current)):
    slug = payload["sub"]
    role = payload.get("role", "candidate")
    if source == "data":
        gj_file = DATA_DIR / f"{name}.geojson"
    elif source == "candidato" and role != "admin":
        gj_file = CANDIDATOS_DIR / slug / f"{name}.geojson"
    else:
        raise HTTPException(403, "Acesso negado.")
    if not gj_file.exists():
        raise HTTPException(404, f"Camada '{name}' não encontrada.")
    gj = _load_json(gj_file)
    if not gj:
        raise HTTPException(500, "Erro ao ler camada.")
    return gj


# ---------------------------------------------------------------------------
# Rotas admin — gestão de candidatos
# ---------------------------------------------------------------------------

@app.get("/api/admin/candidatos-full")
async def admin_list_candidatos_full(payload: dict = Depends(_get_current)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso restrito a administradores.")
    result = []
    if not CANDIDATOS_DIR.exists():
        return result
    for d in sorted(CANDIDATOS_DIR.iterdir()):
        if not d.is_dir():
            continue
        creds = _load_json(d / "credentials.json")
        bases = [f.stem[len("votos_"):] for f in sorted(d.glob("votos_*.geojson"))]
        geojsons = [f.name for f in sorted(d.glob("*.geojson"))]
        result.append({
            "slug": d.name,
            "display_name": creds.get("display_name", d.name) if creds else d.name,
            "email": creds.get("email", "") if creds else "",
            "has_credentials": creds is not None,
            "has_password": bool(creds and creds.get("password_hash")),
            "bases": bases,
            "geojsons": geojsons,
        })
    return result


@app.put("/api/admin/candidato/{slug}/credentials")
async def admin_update_credentials(slug: str, body: CredentialsBody, payload: dict = Depends(_get_current)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso restrito a administradores.")
    folder = CANDIDATOS_DIR / slug
    if not folder.exists():
        raise HTTPException(404, f"Pasta do candidato '{slug}' não encontrada.")
    cred_file = folder / "credentials.json"
    existing = _load_json(cred_file) or {}
    if body.display_name is not None:
        existing["display_name"] = body.display_name
    if body.email is not None:
        existing["email"] = body.email
    if body.password_hash is not None:
        existing["password_hash"] = body.password_hash
    cred_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"message": "Credenciais atualizadas com sucesso.", "slug": slug}


# ---------------------------------------------------------------------------
# Rota admin — acesso a dados de qualquer candidato
# ---------------------------------------------------------------------------

@app.get("/api/admin/candidato/{slug}/votos/{base}")
async def admin_get_votos(slug: str, base: str, payload: dict = Depends(_get_current)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso restrito a administradores.")
    votos_file = CANDIDATOS_DIR / slug / f"votos_{base}.geojson"
    if not votos_file.exists():
        raise HTTPException(404, f"Base '{base}' não encontrada para '{slug}'.")
    gj = _load_json(votos_file)
    if not gj:
        raise HTTPException(500, "Erro ao ler arquivo.")
    is_municipios = "municipio" in base.lower()
    if is_municipios and _cache.get("ce_regioes"):
        return _merge_municipios(gj)
    return _normalize_points(gj)


# ---------------------------------------------------------------------------
# Envio de e-mail (executa em thread separada)
# ---------------------------------------------------------------------------

def _send_reset_email(to_email: str, token: str, display_name: str) -> None:
    reset_url = f"{APP_BASE_URL}/reset-password.html?token={token}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "LocalizaVotos — Redefinição de Senha"
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    html_body = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0e1117;font-family:system-ui,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#1a1d27;border-radius:12px;
              border:1px solid #2d3040;padding:40px;">
    <h2 style="color:#e63946;margin:0 0 8px">LocalizaVotos</h2>
    <p style="color:#8b90a7;margin:0 0 24px;font-size:14px">Plataforma de Análise Eleitoral</p>
    <p style="color:#e8eaf0">Olá, <strong>{display_name}</strong>!</p>
    <p style="color:#b0b3c8">Recebemos uma solicitação de redefinição de senha para sua conta.
    Clique no botão abaixo para criar uma nova senha:</p>
    <div style="text-align:center;margin:32px 0">
      <a href="{reset_url}"
         style="background:#e63946;color:#fff;text-decoration:none;padding:14px 32px;
                border-radius:8px;font-weight:600;font-size:16px;display:inline-block">
        Redefinir Senha
      </a>
    </div>
    <p style="color:#8b90a7;font-size:13px">
      Este link expira em <strong>30 minutos</strong>.<br>
      Se você não solicitou a redefinição, ignore este e-mail — sua senha permanece a mesma.
    </p>
    <hr style="border:none;border-top:1px solid #2d3040;margin:24px 0">
    <p style="color:#555a6e;font-size:12px;word-break:break-all">
      Link alternativo: <a href="{reset_url}" style="color:#e63946">{reset_url}</a>
    </p>
  </div>
</body>
</html>
"""
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"[email] Reset enviado para {to_email}")
    except Exception as exc:
        print(f"[email] Erro ao enviar para {to_email}: {exc}")


# ---------------------------------------------------------------------------
# Servir frontend estático (deve ser o último mount)
# ---------------------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    print(f"[aviso] Frontend não encontrado em {FRONTEND_DIR}")
