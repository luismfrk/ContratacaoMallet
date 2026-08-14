# Banco MySQL

O sistema usa SQLite quando `DATABASE_URL` não está definida e MySQL quando recebe uma URL como:

```text
mysql+pymysql://usuario:senha@servidor:3306/contratacoes?charset=utf8mb4
```

Antes da primeira execução, crie um banco vazio e um usuário exclusivo:

```sql
CREATE DATABASE contratacoes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'contratacoes_app'@'%' IDENTIFIED BY 'uma-senha-forte';
GRANT ALL PRIVILEGES ON contratacoes.* TO 'contratacoes_app'@'%';
FLUSH PRIVILEGES;
```

Defina `DATABASE_URL` no ambiente. Na primeira inicialização, as tabelas são criadas automaticamente.

Para copiar os dados do SQLite atual para um MySQL vazio:

```powershell
$env:DATABASE_URL='mysql+pymysql://contratacoes_app:senha@servidor:3306/contratacoes?charset=utf8mb4'
python scripts/migrar_sqlite_para_mysql.py
```

Depois da mensagem de sucesso, reinicie o servidor. Não apague `data/contratacoes.db`; ele serve como cópia de segurança da migração.
