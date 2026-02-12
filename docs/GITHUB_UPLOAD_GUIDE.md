# Інструкція: Завантаження проекту на GitHub

---

## Крок 1: Створити репозиторій на GitHub

1. Відкрий [github.com](https://github.com)
2. Увійди в свій акаунт
3. Натисни **"+"** → **"New repository"**
4. Заповни:
   - **Repository name**: `telegram-bot-for-unik`
   - **Description**: Документація для розгортання Telegram Bot
   - **Public** або **Private**
   - **☑ Add a README file** ❌ (не став галочку)
5. Натисни **"Create repository"**

---

## Крок 2: Підготувати локальний проект

```bash
# Відкрий термінал (cmd) в папці проекту
cd c:\унік\останній ривок частина 4. етап 2\tg bot for unik\telegram-edu-bot

# Ініціалізуй Git
git init

# Додай всі файли
git add .

# Створи коміт
git commit -m "Додано документацію DevOps: deployment, update, backup, CI/CD"
```

---

## Крок 3: Завантаж на GitHub

```bash
# Додай віддалений репозиторій
git remote add origin https://github.com/YOUR_USERNAME/telegram-bot-for-unik.git

# Завантаж файли
git push -u origin main
```

**Детальніше:**

1. В терміналі виконай:
   ```cmd
   cd c:\унік\останній ривок частина 4. етап 2\tg bot for unik\telegram-edu-bot
   ```

2. Введи:
   ```cmd
   git remote -v
   ```
   Якщо нічого не показує - додай:
   ```cmd
   git remote add origin https://github.com/ТВОЄ_ІМЯ/telegram-bot-for-unik.git
   ```

3. Завантаж:
   ```cmd
   git push -u origin main
   ```

4. Введи логін та пароль від GitHub

---

## Крок 4: Надішліть посилання викладачу

Після успішного завантаження:

1. Відкрий сторінку репозиторію на GitHub
2. Скопіюй посилання:
   ```
   https://github.com/YOUR_USERNAME/telegram-bot-for-unik
   ```
3. Відправ це посилання викладачу

---

## Крок 5: Перевірка

Переконайся, що на GitHub є:

✅ README.md (кореневий)
✅ docs/deployment.md
✅ docs/update.md  
✅ docs/backup.md
✅ docs/scripts/ (всі .sh файли)
✅ .github/workflows/
✅ Dockerfile
✅ docker-compose.yml

---

## Якщо потрібно оновити пізніше:

```bash
# Внеси зміни
git add .
git commit -m "Оновлення документації"
git push origin main
```
