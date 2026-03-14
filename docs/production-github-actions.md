# Mode production GitHub Actions

## Ce que fait GitHub Actions

Le workflow lance exactement :

```bash
poetry run python -m app.batch
```

## Pourquoi c’est important

Si cette commande fonctionne en local, la production suit le même comportement.

## Secrets à garder dans GitHub

- SMTP
- mot de passe mail
- Telegram
- API key

## À retenir

GitHub Actions ne doit jamais contenir une logique différente du local.
