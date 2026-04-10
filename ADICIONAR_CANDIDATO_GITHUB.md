# Adicionar Candidato pelo GitHub Web

> **Nova plataforma (FastAPI + Leaflet.js)**
> Não é mais necessário criar arquivos `.py` nem a pasta `pages/`.
> Basta criar a pasta do candidato com 2 itens: `credentials.json` + arquivos GeoJSON.

---

## Passo a Passo

### 1. Criar a pasta do candidato

1. Acesse: `https://github.com/seu-usuario/localizavotos`
2. Navegue até a pasta `candidatos/`
3. Clique em **"Add file"** → **"Create new file"**
4. No campo de nome, digite: `nome_candidato/credentials.json`
   - Exemplo: `pedro_alves/credentials.json`
   - O GitHub cria a pasta automaticamente ao usar `/`

### 2. Preencher o `credentials.json`

Cole o conteúdo abaixo substituindo os valores em MAIÚSCULAS:

```json
{
  "display_name": "NOME COMPLETO DO CANDIDATO",
  "email": "EMAIL_DO_CANDIDATO@exemplo.com",
  "password_hash": "HASH_SHA256_DA_SENHA"
}
```

**Como gerar o `password_hash`:**

Execute no Python (ou use qualquer gerador SHA-256 online):

```python
import hashlib
senha = "senha_escolhida_aqui"
print(hashlib.sha256(senha.encode()).hexdigest())
```

Exemplo completo:

```json
{
  "display_name": "Pedro Alves",
  "email": "pedro.alves@exemplo.com",
  "password_hash": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
}
```

3. Clique em **"Commit changes"**

---

### 3. Fazer upload dos arquivos GeoJSON

1. Navegue até `candidatos/nome_candidato/`
2. Clique em **"Add file"** → **"Upload files"**
3. Faça upload dos arquivos de votos:
   - `votos_fortaleza.geojson` — pontos por local de votação (Fortaleza)
   - `votos_municipios.geojson` — agrupado por município (visão estadual)
   - `votos_OUTRA_CIDADE.geojson` — qualquer outro município
4. Opcionalmente, adicione camadas auxiliares (bairros, líderes, etc.):
   - `lider_CIDADE.geojson`, `bairros_CIDADE.geojson`, etc.
5. Clique em **"Commit changes"**

---

## Estrutura de Pastas

```
candidatos/
├── candidato_teste/
│   ├── credentials.json          ← autenticação
│   ├── votos_fortaleza.geojson
│   └── votos_municipios.geojson
├── larissa_gaspar/
│   ├── credentials.json
│   ├── votos_fortaleza.geojson
│   └── votos_municipios.geojson
└── pedro_alves/                  ← novo candidato
    ├── credentials.json          ← arquivo 1
    ├── votos_fortaleza.geojson   ← arquivo 2
    └── votos_municipios.geojson  ← arquivo 3
```

---

## Formato do GeoJSON de Votos

### votos_fortaleza.geojson (pontos por local)

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [-38.5432, -3.7197] },
      "properties": {
        "NM_LOCAL_VOTACAO": "ESCOLA ESTADUAL EXEMPLO",
        "NM_MUNICIPIO": "FORTALEZA",
        "Bairro/Distrito": "ALDEOTA",
        "QT_VOTOS": 87,
        "NR_ZONA": "001"
      }
    }
  ]
}
```

### votos_municipios.geojson (agrupado por município)

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [-39.3, -5.1] },
      "properties": {
        "NM_MUNICIPIO": "FORTALEZA",
        "QT_VOTOS": 4250
      }
    }
  ]
}
```

> Para a visão estadual (`votos_municipios`), o backend funde automaticamente os dados
> com os polígonos de `data/ce_regioes.geojson` para gerar o mapa coroplético.
> O campo `NM_MUNICIPIO` deve estar em **MAIÚSCULAS** para o match funcionar.

---

## Campos reconhecidos automaticamente

| Campo no GeoJSON | Aliases aceitos |
|---|---|
| Município | `NM_MUNICIPIO`, `municipio`, `Municipio`, `NM_MUN` |
| Votos | `QT_VOTOS`, `qt_votos`, `votos`, `qtde_votos` |
| Local de votação | `NM_LOCAL_VOTACAO`, `local_votacao`, `local` |
| Bairro / Distrito | `Bairro/Distrito`, `BAIRRO`, `bairro`, `Distrito` |
| Latitude | `Latitude`, `lat`, `LAT` |
| Longitude | `Longitude`, `lon`, `LON`, `lng` |

---

## Verificação após o deploy

1. Aguarde o deploy automático (Railway detecta o push no GitHub)
2. Acesse: `https://seu-dominio.railway.app`
3. Selecione o candidato no dropdown e faça login com a senha definida
4. O mapa deve carregar com os dados do candidato

---

## Dicas

- Use nomes em **minúsculas** e **underscores**: `pedro_alves`, não `Pedro Alves`
- O nome da pasta é o **username** de login do candidato
- O `password_hash` é **SHA-256** da senha (compatível com o app anterior)
- O campo `email` é obrigatório para o recurso de **recuperação de senha**
- Camadas auxiliares com nome diferente de `votos_*` aparecem automaticamente
  no painel como camadas opcionais (ex: `lider_quixeramobim.geojson` → "Lider Quixeramobim")
- A senha pode ser alterada diretamente editando `password_hash` no GitHub
  ou pelo fluxo de recuperação de senha na própria aplicação

---

## Variáveis de Ambiente (Railway Settings → Variables)

| Variável | Descrição |
|---|---|
| `SECRET_KEY` | Chave de assinatura JWT (obrigatória em produção) |
| `ADMIN_PASSWORD_HASH` | Hash SHA-256 da senha do admin |
| `ADMIN_EMAIL` | E-mail do admin para recuperação de senha |
| `SMTP_HOST` | Servidor SMTP (ex: `smtp.gmail.com`) |
| `SMTP_PORT` | Porta SMTP (padrão: `587`) |
| `SMTP_USER` | Remetente dos e-mails |
| `SMTP_PASSWORD` | Senha ou App Password SMTP |
| `APP_BASE_URL` | URL pública da aplicação (ex: `https://localizavotos.up.railway.app`) |
