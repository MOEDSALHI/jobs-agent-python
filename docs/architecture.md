# Architecture du projet

## Vue d’ensemble

L’application repose sur une idée simple : récupérer des offres d’emploi Python depuis plusieurs job boards, filtrer uniquement les offres utiles, puis envoyer seulement les nouvelles offres.

## Flux principal

1. Les scrapers interrogent les sites (**APEC**, **Welcome to the Jungle**, **HelloWork**).
2. Les offres sont regroupées.
3. Un filtrage applique vos mots-clés.
4. Un score priorise les offres.
5. Un fichier JSON garde l’historique.
6. Email / Telegram notifient uniquement les nouveautés.

## Fichiers centraux

- `app/runner.py` → moteur principal  
- `app/batch.py` → exécution batch  
- `app/main.py` → API FastAPI  
- `app/store.py` → gestion du state JSON  
- `state/jobs.json` → historique des offres  
- `app/scrapers/` → extraction des offres  

## Règle importante

`runner.py` doit rester la source unique de la logique métier.