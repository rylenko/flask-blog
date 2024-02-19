<h1 align="center">Welcome to Flask-Blog 🌿</h1>

This blog project is a test and overflowed with various functions.
The main thing that is in the project - **Full control over posts, tags and comments**.
Also, there is a lot of functionality for **working with the account, mail tokens, sessions, notifications, etc**.

**Warning:** In this project in **some places** we work with **third-party javascripts** such as google, recaptcha, etc.

<h1 align="center">Installation</h1>

**1.** Clone this repository how you like it.

**2.** Create the second required .env file with the following options **(flask-blog/blog/.env)**.
```
SENTRY_DSN(optional), SECRET_KEY, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER_NAME, RECAPTCHA_PUBLIC_KEY, RECAPTCHA_PRIVATE_KEY, GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET, CELERY_BROKER_URL
```

**3.1.** To test the performance of the project. **Note**: During the first test `GITHUB_OAUTH_ACCESS_TOKEN` must be specified to register samples (cassettes) of OAuth requests in `TestingConfig.OAUTH_CASSETTES_DIR`. After the first successful tests this parameter can be permanently deleted from `.env`.
```
$ cd blog/
$ pip3 install poetry psycopg2-binary
$ poetry install
$ pytest
```

**3.2.** In addition, you can check the quality of the code if you need it. **Note**: For some reason `mypy` cannot define everything related to `flask-sqlalchemy.SQLAlchemy`, so try to ignore it.
```
$ cd blog/
$ pip3 install poetry psycopg2-binary
$ poetry install
$ sudo chmod a+x lint.sh
$ ./lint.sh
```

**4.** Launch docker and all needed services.
```
$ docker-compose up --build
```

**5.** Come inside 'blog' docker container.
```
$ docker exec -it blog bash
```

**6.** Create admin user.
```
$ flask create admin
```
