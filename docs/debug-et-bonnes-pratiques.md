# Debug et bonnes pratiques

## Quand un scraper casse

Toujours commencer par :

```bash
poetry run python scratch_test.py
```

## Quand aucun mail n’arrive

Tester :

```bash
poetry run python -m app.batch
```

## Vérifier la state json

```bash
cat state/jobs.json
```

## Bon réflexe

Avant chaque push :

```bash
poetry run python -m app.batch
```