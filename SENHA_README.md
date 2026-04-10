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

### Erro comum no Railway

Não use o botão de **“secret” / `${{ secret(...) }}`** do Railway para preencher `ADMIN_PASSWORD_HASH`.  
Esse valor é **aleatório** e **não** é o hash da sua senha — o login **sempre falhará**.

O correto é colar manualmente o resultado de:

```python
import hashlib
print(hashlib.sha256("a_senha_que_voce_vai_digitar_no_login".encode()).hexdigest())
```

São **64 caracteres** hexadecimais (`0-9` e `a-f`), por exemplo:  
`240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9` (exemplo para a senha `admin123`).

No login use **usuário** `admin` (ou o valor de `ADMIN_USERNAME`, se definiu) e a **mesma senha em texto** que você usou no Python acima.

---

Passos:

1. Vá em **Variables** no serviço Railway
2. Crie `ADMIN_PASSWORD_HASH` colando o **hash SHA-256** (não a senha em claro)
3. Crie `SECRET_KEY` (ex.: `python -c "import secrets; print(secrets.token_hex(32))"`)
4. Crie `ADMIN_EMAIL` com seu e-mail
5. (Opcional) Crie `ADMIN_USERNAME` se quiser outro login além de `admin`
6. Faça redeploy

No **login** use: usuário = valor de `ADMIN_USERNAME` ou `admin`, e a senha em texto plano (a que você usou para gerar o hash).

## Sincronizar credenciais com o GitHub (opcional)

Ao salvar candidato no painel admin, o backend pode enviar o `credentials.json` para o repositório (API Contents do GitHub).

| Variável | Exemplo | Descrição |
|----------|---------|-----------|
| `GITHUB_TOKEN` | `ghp_...` ou PAT fine-grained | Token com permissão de **conteúdo** no repositório (ler e gravar arquivos) |
| `GITHUB_OWNER` | `pauloqxm` | Dono do repositório |
| `GITHUB_REPO` | `localizavotos` | Nome do repositório |
| `GITHUB_BRANCH` | `main` | Branch (opcional; padrão `main`) |

Crie o token em GitHub → **Settings → Developer settings → Personal access tokens**. Para fine-grained: acesse só o repositório `localizavotos` e marque **Contents: Read and write**.

⚠️ O token é sensível: guarde só nas variáveis do Railway, nunca no código.

## Segurança

⚠️ **IMPORTANTE**: Altere a senha padrão imediatamente após o primeiro acesso!

As subpáginas (candidatos) permanecem acessíveis diretamente sem senha.
