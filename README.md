# waai

Plantilla base para desplegar un bot de WhatsApp (FAQ, precio, enlace de acción, derivación a
humano) sobre la API oficial de WhatsApp Cloud de Meta. Python/FastAPI + SQLite, sin
dependencias pesadas (sin Docker, sin base de datos externa, sin Node).

**Regla de diseño del bot: solo responde, nunca inicia conversación.** Esto lo mantiene dentro
del rango gratuito y de menor riesgo de la API de WhatsApp (ver "Costos" abajo).

## Qué necesitas antes de empezar

1. **Un servidor propio** con Ubuntu, nginx y certbot instalados, con un dominio/subdominio
   apuntando a su IP pública. Opciones con capa gratuita razonable: AWS (hasta $200 USD en
   créditos, 6 meses para cuentas nuevas) u Oracle Cloud ("Always Free", permanente).
2. **Un número de teléfono real** dedicado a WhatsApp Business (no puede tener WhatsApp normal
   activo al mismo tiempo).
3. **Una app de Meta for Developers** (tipo "Business") con el producto WhatsApp agregado.

## Setup de Meta (resumen)

1. Crea la app en developers.facebook.com, agrega el producto WhatsApp.
2. Registra tu número real: API Setup → Add phone number → verificación por SMS/llamada.
3. Si al registrar el número (`POST /{phone_number_id}/register`) te da un error de "Unverified
   WABA", pasa la app a modo **Live** — no siempre hace falta la verificación completa del
   negocio, dependiendo del caso.
4. Suscribe la app a los eventos de la WABA: `POST /{waba_id}/subscribed_apps` con tu token.
5. Crea un System User (Meta Business Suite → Configuración del negocio → Usuarios) con permisos
   `whatsapp_business_management` y `whatsapp_business_messaging`, y genera un token
   **permanente** (no expira).
6. Publica una Privacy Policy y Terms of Service reales (puedes usar las de otro proyecto como
   base) — Meta las pide en App settings → Basic.
7. Copia el **App Secret** (App settings → Basic → botón "Show") y guárdalo como
   `WHATSAPP_APP_SECRET` en tu `.env` — el bot lo usa para verificar que cada webhook viene
   realmente de Meta (firma `X-Hub-Signature-256`). Sin esto el bot no arranca.

**Si vas a tener mas de un bot/WABA bajo el mismo Business Portfolio** (varios proyectos de un
mismo negocio, por ejemplo), considera verificar el negocio ante Meta desde el principio — sin
verificacion, Meta limita cuantas WABAs puede crear un Business Portfolio, y te puedes topar con
ese limite justo cuando estas registrando el segundo o tercer numero.

## Setup del proyecto

```bash
git clone <este-repo> mi-bot
cd mi-bot
cp .env.example .env         # llena tus credenciales reales, NUNCA subas este archivo a git
# edita config/business.yaml con los datos de tu negocio
# agrega tus archivos .md reales a knowledge/ (borra EJEMPLO.md)

sudo ./deploy/install.sh tudominio.com 8002 /opt/bots/mi-bot
# copia tu .env real a /opt/bots/mi-bot/.env, revisa business.yaml/knowledge ahi tambien
sudo systemctl enable --now mi-bot
```

Registra en Meta (WhatsApp → Configuration, y también en App Dashboard → Webhooks →
`whatsapp_business_account` — son dos pantallas separadas, ambas necesarias):
- Callback URL: `https://tudominio.com/webhook`
- Verify Token: el mismo valor que pusiste en `.env` como `WHATSAPP_VERIFY_TOKEN`

## Pruebas

```bash
cd /opt/bots/mi-bot
sudo -u www-data .venv/bin/python test_main.py
```

## Costos

- **WhatsApp**: gratis para este diseño (bot reactivo). Meta solo cobra mensajes que el negocio
  inicia (plantillas fuera de la ventana de 24h); los mensajes que el cliente escribe primero y
  las respuestas dentro de esas 24h no tienen costo.
- **LLM**: depende del proveedor que uses (Anthropic, o cualquier endpoint compatible con OpenAI
  como Nvidia NIM, OpenRouter, Kimi) — revisa su propio dashboard de facturación.
- **Servidor**: el de tu cuenta de AWS/Oracle Cloud (ver capas gratuitas arriba).

## Estructura

```
agent/main.py        # webhook + loop del agente (generico, no tocar por proyecto)
agent/memory.py       # historial de conversacion en SQLite
config/business.yaml  # nombre, tono, precio, enlace de accion - edita esto por proyecto
knowledge/*.md         # tu FAQ/catalogo/politicas - el bot solo responde con lo que hay aqui
deploy/install.sh      # automatiza venv + systemd + nginx + certbot
```
