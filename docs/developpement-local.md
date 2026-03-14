# Mode développement local

## Commandes principales

### Tester uniquement les scrapers

```bash
poetry run python scratch_test.py
```

Cela affiche les offres trouvées sans envoyer de mail.

### Tester le vrai flux complet

```bash
poetry run python -m app.batch
```

Cela exécute :

- scraping
- filtrage
- scoring
- base SQLite
- email

### Tester l’API locale

```bash
poetry run uvicorn app.main:app --reload
```

## Ordre conseillé

1. Modifier le code  
2. Tester avec `scratch_test.py`  
3. Valider avec `app.batch`  
4. Tester l’API si besoin  
