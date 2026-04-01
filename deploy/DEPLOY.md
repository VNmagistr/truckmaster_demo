# Деплой демо на demo.ital-truck.com.ua

## Передумови
- DNS: A-записи `demo.ital-truck.com.ua` і `api.demo.ital-truck.com.ua` → `157.230.114.19`
- SSH доступ до сервера: `ssh ubuntu@157.230.114.19`

---

## 1. Клонування репозиторіїв

```bash
cd /home/ubuntu

# Бекенд
git clone https://github.com/VNmagistr/truckmaster_demo.git
cd truckmaster_demo
git checkout demo/v2.5

# Фронтенд
cd /home/ubuntu
git clone https://github.com/VNmagistr/truckmaster_frontend_demo.git
cd truckmaster_frontend_demo
git checkout demo/v2.5
```

---

## 2. Налаштування бекенду

```bash
cd /home/ubuntu/truckmaster_demo

# Віртуальне середовище
python3 -m venv venv
source venv/bin/activate
pip install -r my_iveco_crm/requirements.txt

# .env
cp deploy/.env.demo-server .env
nano .env   # змінити SECRET_KEY на будь-який довгий рядок

# Міграції та демо-дані
cd my_iveco_crm
python manage.py migrate
python manage.py create_demo_data
python manage.py collectstatic --noinput
```

---

## 3. Налаштування фронтенду

```bash
cd /home/ubuntu/truckmaster_frontend_demo

# Node.js (якщо не встановлено)
# curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
# sudo apt install -y nodejs

npm install

# .env для збірки
echo "VITE_API_URL=https://api.demo.ital-truck.com.ua/api" > .env

# Збірка
npm run build
# Результат: ./dist/
```

---

## 4. Systemd сервіс для gunicorn

```bash
sudo cp /home/ubuntu/truckmaster_demo/deploy/gunicorn-demo.service \
        /etc/systemd/system/gunicorn-demo.service

sudo systemctl daemon-reload
sudo systemctl enable gunicorn-demo
sudo systemctl start gunicorn-demo

# Перевірка
sudo systemctl status gunicorn-demo
```

---

## 5. Nginx

```bash
# Копіюємо конфіги
sudo cp /home/ubuntu/truckmaster_demo/deploy/nginx-frontend.conf \
        /etc/nginx/sites-available/demo.ital-truck.com.ua

sudo cp /home/ubuntu/truckmaster_demo/deploy/nginx-backend.conf \
        /etc/nginx/sites-available/api.demo.ital-truck.com.ua

# Активуємо
sudo ln -s /etc/nginx/sites-available/demo.ital-truck.com.ua \
           /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/api.demo.ital-truck.com.ua \
           /etc/nginx/sites-enabled/

# Перевірка та перезапуск
sudo nginx -t && sudo systemctl reload nginx
```

---

## 6. SSL (Let's Encrypt)

```bash
sudo certbot --nginx \
    -d demo.ital-truck.com.ua \
    -d api.demo.ital-truck.com.ua
```

Certbot сам змінить Nginx конфіги та налаштує авто-оновлення.

---

## 7. Перевірка

- Фронтенд: https://demo.ital-truck.com.ua
- Бекенд API: https://api.demo.ital-truck.com.ua/api/docs/
- Адмінка: https://api.demo.ital-truck.com.ua/admin/
  - Логін: `admin` / Пароль: `demo1234`

---

## Оновлення демо (після змін у репо)

```bash
# Бекенд
cd /home/ubuntu/truckmaster_demo
git pull
source venv/bin/activate
cd my_iveco_crm
pip install -r requirements.txt   # якщо змінились залежності
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn-demo

# Фронтенд
cd /home/ubuntu/truckmaster_frontend_demo
git pull
npm install
npm run build
sudo systemctl reload nginx
```

---

## Скидання демо-даних

```bash
cd /home/ubuntu/truckmaster_demo/my_iveco_crm
source ../venv/bin/activate
rm db.sqlite3
python manage.py migrate
python manage.py create_demo_data
sudo systemctl restart gunicorn-demo
```
