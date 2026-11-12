# PESO Pio Duran Job Portal on MySQL (VPS)

The app uses **SQLite on the laptop** and **MySQL on the VPS**. Which one is used
depends only on `.env` (`DB_ENGINE=mysql`). No code change is needed.

Tested: all 33 migrations apply on MySQL, and copying the current data from
SQLite to MySQL keeps every record (users, jobs, applications).

---

## 0. Requirements on the VPS

* **MySQL 8.0.11+ or MariaDB 10.5+** (Django 5.2 refuses older servers).
  Check with:

  ```bash
  mysql -V
  ```

* Packages needed to build `mysqlclient` (Ubuntu/Debian):

  ```bash
  sudo apt update
  sudo apt install -y python3-dev python3-venv build-essential pkg-config default-libmysqlclient-dev
  ```

## 1. Create a separate database and user

This does **not** touch the Comelec or Water System databases. The new user can
only see `pioduran_job`.

```bash
sudo mysql
```

```sql
CREATE DATABASE pioduran_job CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'pioduran'@'localhost' IDENTIFIED BY 'PUT-A-STRONG-PASSWORD-HERE';
GRANT ALL PRIVILEGES ON pioduran_job.* TO 'pioduran'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 2. Load MySQL time zone tables (required)

The reports, charts and date filters convert dates to `Asia/Manila`. MySQL
needs its time zone tables for that, otherwise those pages show an error.
Run once per server (safe for the other projects):

```bash
mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql -u root mysql
```

Check (must print a date, not NULL):

```sql
SELECT CONVERT_TZ('2026-01-01 00:00:00', 'UTC', 'Asia/Manila');
```

## 3. `.env` on the VPS

```ini
DEBUG=False
SECRET_KEY=<long random string>

DB_ENGINE=mysql
DB_NAME=pioduran_job
DB_USER=pioduran
DB_PASSWORD=PUT-A-STRONG-PASSWORD-HERE
DB_HOST=127.0.0.1
DB_PORT=3306
```

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 4. Install and migrate

From the project folder on the VPS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

## 5. Choose: fresh start **or** bring the laptop data

### A. Fresh start (recommended for the real launch)

```bash
python manage.py create_peso_admin <admin-username>
```

### B. Copy the data from the laptop

On the **laptop** (clear the demo data first if you do not want it):

```bash
.\.venv\Scripts\python.exe manage.py seed_demo_data --clear
.\.venv\Scripts\python.exe -X utf8 manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission -e sessions -e admin.logentry --indent 2 -o data.json
```

Upload `data.json`, plus the `media/` and `private_uploads/` folders (resumes,
logos, certificates), to the project folder on the VPS. Then on the **VPS**,
after step 4:

```bash
python manage.py loaddata data.json
rm data.json
```

`data.json` contains personal data. Delete it from the laptop and the VPS after
loading.

### C. Demo data for the presentation (optional)

Adds 15 employers, 15 jobs in Pio Duran, Albay and 15 applicants, all with the
password `Testing@123` (logins `employer01`-`employer15`, `applicant01`-`applicant15`).
`--force` is needed because `DEBUG` is off on the VPS:

```bash
python manage.py seed_demo_data --force          # add
python manage.py seed_demo_data --clear --force  # remove before the real launch
```

`--clear` deletes only the sample accounts (emails ending in `@pioduran-demo.test`)
and their uploaded files.

## 6. Backups

```bash
mysqldump -u pioduran -p pioduran_job > pioduran_job_$(date +%F).sql
```

Back up `media/` and `private_uploads/` too. They hold the uploaded files.

---

### Notes

* Running the tests against MySQL: 7 tests that download a file
  (resume/certificate) fail **only inside the test runner**. Closing the file
  response makes Django close the connection in the middle of the test's
  transaction. The real app is not affected, and all tests pass on SQLite,
  which is what `manage.py test` uses on the laptop.
* Still to set for the VPS (separate from the database): `ALLOWED_HOSTS` and
  `CSRF_TRUSTED_ORIGINS` for your domain or IP, gunicorn, nginx, and HTTPS.
