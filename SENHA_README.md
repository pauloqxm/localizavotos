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

## Configuração no Railway

Para configurar a senha no Railway sem alterar o código:

1. Vá em Settings → Variables
2. Adicione uma variável: `ADMIN_PASSWORD_HASH`
3. Cole o hash SHA256 da sua senha
4. Redeploy a aplicação

## Segurança

⚠️ **IMPORTANTE**: Altere a senha padrão imediatamente após o primeiro acesso!

As subpáginas (candidatos) permanecem acessíveis diretamente sem senha.
