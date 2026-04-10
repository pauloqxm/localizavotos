# Configuração de Senha

## Senha Padrão
A senha padrão atual é: **admin123**

## Como Alterar a Senha

1. Escolha sua nova senha
2. Gere o hash SHA256 da senha usando Python:

```python
import hashlib
senha = "sua_nova_senha_aqui"
hash_senha = hashlib.sha256(senha.encode()).hexdigest()
print(hash_senha)
```

3. Substitua o valor de `senha_hash` no arquivo `app.py` (linha ~14) pelo novo hash

## Configuração no Railway (FastAPI / login web)

Não existe uma variável chamada apenas `ADMIN`. Use estas (o nome do login padrão é `admin`):

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `SECRET_KEY` | Sim | Chave aleatória longa para assinar os tokens JWT |
| `ADMIN_PASSWORD_HASH` | Sim | Hash SHA-256 da senha do administrador |
| `ADMIN_EMAIL` | Sim | E-mail do admin (recuperação de senha) |
| `ADMIN_USERNAME` | Não | Login do admin (padrão: `admin`) |
| `APP_BASE_URL` | Recomendado | URL pública do app (ex: `https://seu-app.up.railway.app`) |

Passos:

1. Vá em **Variables** no serviço Railway
2. Crie `ADMIN_PASSWORD_HASH` com o hash SHA-256 da sua senha
3. Crie `SECRET_KEY` (ex.: `python -c "import secrets; print(secrets.token_hex(32))"`)
4. Crie `ADMIN_EMAIL` com seu e-mail
5. (Opcional) Crie `ADMIN_USERNAME` se quiser outro login além de `admin`
6. Faça redeploy

No **login** use: usuário = valor de `ADMIN_USERNAME` ou `admin`, e a senha em texto plano (a que você usou para gerar o hash).

## Segurança

⚠️ **IMPORTANTE**: Altere a senha padrão imediatamente após o primeiro acesso!

As subpáginas (candidatos) permanecem acessíveis diretamente sem senha.
