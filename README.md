# Дипломный проект профессии «Python-разработчик: расширенный курс»

## Backend-приложение для автоматизации закупок

Для запуска приложения необходимо установить следующие приложения:
1. [Python 3.10+](https://www.python.org/)
2. [Docker](https://www.docker.com/)
3. [Docker Compose](https://docs.docker.com/compose/install/)
4. Клонировать репозиторий
```bash 
    git clone https://github.com/magic-kch/python-final-diplom.git
    cd python-final-diplom
```
Внести свои данные в файлы `_env` и `pg.env`
```
# email parameters
# db parameters
```
## Запуск приложения
```bash
    docker-compose up -d
```

## API доступно по адресу `http://127.0.0.1/api/v1/`

#### Полное описание API находится в [API_DOCS.md](./API_DOCS.md)
