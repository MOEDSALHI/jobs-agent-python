# jobs-agent-python

Application de veille automatisée d’offres d’emploi Python, conçue comme base évolutive vers un assistant intelligent de recherche d’opportunités intégrant progressivement des approches IA / LLM.

L’application récupère des offres depuis plusieurs job boards français, applique un filtrage métier, conserve uniquement les nouvelles annonces pertinentes, puis déclenche des notifications.

---

## Objectif du projet

Le projet répond à un besoin simple :

automatiser la recherche d’offres Python de manière fiable, reproductible et exploitable.

L’objectif technique est double :

* construire une base robuste de scraping et de traitement,
* préparer une évolution progressive vers des mécanismes de sélection plus intelligents.

Aujourd’hui, le projet fonctionne sur des règles explicites.

À terme, il pourra intégrer :

* classification intelligente des offres,
* scoring enrichi par IA,
* résumé automatique des missions,
* aide à la décision via LLM.

---

## Fonctionnalités actuelles

* Scraping multi-sources via Playwright
* Filtrage par mots-clés métier
* Scoring simple des offres
* Déduplication SQLite
* Notification email
* Notification Telegram (optionnelle)
* API FastAPI
* Exécution batch locale
* Automatisation GitHub Actions

---

## Sources actuellement utilisées

* APEC
* HelloWork
* Welcome to the Jungle

L’architecture permet d’ajouter facilement d’autres sources.

---

## Lancement rapide en local

### Installation des dépendances

```bash
poetry install
```

### Installation du navigateur Chromium

```bash
poetry run playwright install --with-deps chromium
```

### Test rapide des scrapers

```bash
poetry run python scratch_test.py
```

### Exécution complète locale

```bash
poetry run python -m app.batch
```

### Lancement de l’API locale

```bash
poetry run uvicorn app.main:app --reload
```

---

## Méthode de travail : local et production

Le principe du projet est volontairement simple :

ce qui fonctionne localement doit être exactement ce qui fonctionne en production.

### Développement local

En local :

* scratch_test.py permet de tester rapidement les scrapers
* app.batch exécute tout le flux métier
* FastAPI permet d’exposer localement les résultats

### Production

En production, GitHub Actions exécute exactement :

```bash
poetry run python -m app.batch
```

Cela garantit :

* un seul flux métier,
* pas de divergence local / production,
* validation simple avant déploiement.

---

## Docker

### Lancement

```bash
docker compose up --build
```

### Services disponibles

* API : http://localhost:8000
* SQLite Web : http://localhost:8080

---

## Documentation du projet

* [Architecture](docs/architecture.md)
* [Mode développement local](docs/developpement-local.md)
* [Mode production GitHub Actions](docs/production-github-actions.md)
* [Debug](docs/debug-et-bonnes-pratiques.md)
* [Roadmap](docs/roadmap.md)

---

## Structure principale

```text
app/
├── runner.py
├── batch.py
├── main.py
├── config.py
├── store.py
├── scoring.py
├── notify_email.py
├── notify_telegram.py
└── scrapers/
```

---

## Principe important

`runner.py` reste le point central de la logique métier.

Toute évolution fonctionnelle doit converger vers ce point unique afin de conserver :

* simplicité,
* testabilité,
* cohérence local / production.

---

## Vision d’évolution

Le projet n’a pas vocation à rester un simple scraper.

L’évolution naturelle consiste à construire progressivement un assistant capable :

* d’identifier les offres réellement pertinentes,
* de comprendre leur contenu réel,
* de prioriser automatiquement les opportunités.

Les futures briques IA / LLM seront ajoutées progressivement sans casser la base existante.
