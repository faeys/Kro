# 🤖 Mi Bot de Telegram

Bot con sistema de keys y panel de administrador.

---

## ⚙️ Configuración (IMPORTANTE — hacer primero)

### Paso 1 — Obtener el Token
1. Abre Telegram y busca **@BotFather**
2. Escribe `/newbot` y sigue los pasos
3. Al final te da un token así: `7412365890:AAFxyz123...`
4. Cópialo

### Paso 2 — Obtener tu ID de Telegram
1. Busca **@userinfobot** en Telegram
2. Escríbele cualquier cosa
3. Te responde con tu ID numérico, ej: `123456789`
4. Cópialo

---

## 🚀 Subir a Railway (gratis, 24/7)

1. Crea cuenta en [railway.app](https://railway.app)
2. Crea un nuevo proyecto → **"Deploy from GitHub"**
   - (sube esta carpeta a un repo de GitHub primero)
   - O usa **"Empty Project"** y sube los archivos manualmente
3. En Railway, ve a tu proyecto → **Variables** → agrega:

   | Variable   | Valor                        |
   |------------|------------------------------|
   | `BOT_TOKEN` | el token de @BotFather      |
   | `ADMIN_IDS` | tu ID numérico (ej: `123456789`) |

4. Railway detecta el `Procfile` y arranca el bot solo ✅

---

## 💻 Correr en local (opcional)

```bash
pip install -r requirements.txt

# Windows
set BOT_TOKEN=tu_token
set ADMIN_IDS=tu_id

# Mac/Linux
export BOT_TOKEN=tu_token
export ADMIN_IDS=tu_id

python bot.py
```

---

## 👑 Comandos de Admin (solo tú)

| Comando | Función |
|---|---|
| `/genkey` | Genera 1 key |
| `/genkey 5` | Genera 5 keys |
| `/listkeys` | Ver keys disponibles y usadas |
| `/listusers` | Ver usuarios registrados |
| `/ban 123456` | Banear usuario por ID |
| `/unban 123456` | Desbanear usuario |
| `/revokekey ABC` | Eliminar una key sin usar |
| `/stats` | Estadísticas del bot |

## 👤 Comandos de Usuario

| Comando | Función |
|---|---|
| `/start` | Registrarse con una key |
| `/menu` | Menú principal |

---

## 🔑 Flujo de registro

1. Usuario escribe `/start`
2. Bot pide una key
3. Tú generas la key con `/genkey` y se la mandas
4. Usuario la ingresa → acceso concedido
5. Te llega una notificación automática

---

## ➕ Agregar funciones propias

Busca esta sección en `bot.py` y agrega tus comandos ahí:

```python
app.add_handler(CommandHandler("micomando", mi_funcion))
```

Y decora tu función con `@registered_only` para que solo usuarios con acceso puedan usarla.
