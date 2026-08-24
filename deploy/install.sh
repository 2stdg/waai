#!/usr/bin/env bash
# Instala y despliega este bot en un servidor Ubuntu con nginx ya instalado.
# Uso: sudo ./install.sh <dominio> <puerto_local> <ruta_del_proyecto>
# Ejemplo: sudo ./install.sh mibot.midominio.com 8002 /opt/bots/mibot
set -euo pipefail

DOMAIN="${1:?Uso: install.sh <dominio> <puerto_local> <ruta_del_proyecto>}"
PORT="${2:?Uso: install.sh <dominio> <puerto_local> <ruta_del_proyecto>}"
PROJECT_DIR="${3:?Uso: install.sh <dominio> <puerto_local> <ruta_del_proyecto>}"
SERVICE_NAME="$(basename "$PROJECT_DIR")"

echo "==> Copiando proyecto a $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"
cp -r "$(dirname "$0")/../agent" "$(dirname "$0")/../config" "$(dirname "$0")/../knowledge" \
      "$(dirname "$0")/../requirements.txt" "$(dirname "$0")/../.env.example" "$PROJECT_DIR/"

if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "==> No hay .env en $PROJECT_DIR - copia .env.example a .env y llena tus valores antes de arrancar el servicio."
  cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
fi

echo "==> Creando entorno virtual"
python3 -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/pip" install -q -r "$PROJECT_DIR/requirements.txt"

echo "==> Creando servicio systemd $SERVICE_NAME"
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=${SERVICE_NAME} WhatsApp bot (waai template)
After=network.target

[Service]
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/.venv/bin/uvicorn main:app --host 127.0.0.1 --port ${PORT} --app-dir ${PROJECT_DIR}/agent
Restart=on-failure
MemoryMax=300M
MemoryHigh=250M
User=www-data

[Install]
WantedBy=multi-user.target
EOF

echo "==> Configurando nginx para ${DOMAIN}"
mkdir -p "/var/www/${DOMAIN}"
echo "<h1>${DOMAIN}</h1>" > "/var/www/${DOMAIN}/index.html"

cat > "/etc/nginx/sites-available/${DOMAIN}" <<EOF
server {
    listen 80;
    listen [::]:80;

    server_name ${DOMAIN};

    root /var/www/${DOMAIN};
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location /webhook {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 35s;
    }
}
EOF
ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
nginx -t && systemctl reload nginx

echo "==> Pidiendo certificado HTTPS con certbot"
certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --register-unsafely-without-email --redirect

chown -R www-data:www-data "$PROJECT_DIR" "/var/www/${DOMAIN}"

echo "==> Listo. Antes de arrancar:"
echo "    1. Edita ${PROJECT_DIR}/.env con tus credenciales reales."
echo "    2. Edita ${PROJECT_DIR}/config/business.yaml y agrega tus archivos a ${PROJECT_DIR}/knowledge/"
echo "    3. systemctl enable --now ${SERVICE_NAME}"
