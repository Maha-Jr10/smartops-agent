# Monitoring cloud

Les services de production sont hébergés séparément :

- **API et Evidently sur Railway** : les dépendances MLOps sont installées par `railway.toml`.
  Les rapports de dérive sont envoyés vers le bucket Supabase `reports`.
- **MLflow sur DagsHub** : les traces et les rapports Evidently sont journalisés dans
  l'expérience MLflow `smartops-agent-monitoring`.
- **Métriques sur Grafana Cloud** : le service Alloy Railway existant collecte `/metrics/`
  sur l'URL de l'API et les envoie au Prometheus distant.

## Configuration des services

Dans Railway, gardez le service API configuré avec `railway.toml`. Ajoutez les variables
suivantes au service API, dans l'onglet Variables :

| Variable | Valeur |
|---|---|
| `MLFLOW_TRACKING_URI` | `https://dagshub.com/Maha-Jr10/smartops-agent.mlflow` |
| `MLFLOW_TRACKING_USERNAME` | `Maha-Jr10` |
| `MLFLOW_TRACKING_PASSWORD` | Jeton d'accès DagsHub, comme variable secrète |
| `SUPABASE_URL` | URL du projet Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Clé service-role, comme variable secrète |

Le service de collecte Alloy existe déjà dans Railway et utilise
`docker/alloy/Dockerfile` avec `docker/alloy/config.alloy`. Ne créez pas de second
collecteur. Vérifiez que ces variables sont configurées sur ce service :

| Variable | Valeur |
|---|---|
| `GRAFANA_PROM_URL` | URL « Remote Write » fournie par la page Prometheus de Grafana Cloud |
| `GRAFANA_PROM_USERNAME` | Identifiant Prometheus fourni par Grafana Cloud |
| `GRAFANA_PROM_PASSWORD` | Jeton Access Policy Grafana Cloud avec permission `metrics:write`, comme variable secrète |

Dans Grafana Cloud, sélectionnez la source de données Prometheus Cloud et importez
`monitoring/grafana/dashboards/smartops.json` avec Dashboards > New > Import. Les
métriques proviennent des requêtes réelles ; l'injection des traces de démo seule ne
crée pas de trafic Prometheus.

## Rapports de dérive

Le bouton d'injection de données ou le scheduler de l'API lance Evidently. Le rapport
HTML est enregistré localement pendant l'exécution, envoyé à Supabase Storage et
journalisé comme artefact dans l'expérience DagsHub MLflow
`smartops-agent-monitoring`. Les mêmes variables d'accès MLflow sont utilisées pour
la journalisation des traces de l'agent. Le scheduler génère aussi un rapport au
démarrage puis toutes les six heures. Pour conserver les fichiers JSONL entre les
redéploiements Railway, attachez un volume Railway au service API, monté sur
`/app/reports`.

Le rapport est également disponible via l'API protégée `GET /report/drift` et
dans Supabase Storage, bucket `reports`, objet `monitoring/drift_report.html`.

En local, les dépendances optionnelles s'installent avec `uv sync --extra mlops`.
Utilisez `make monitor` pour générer un rapport local. La pile `docker-compose.yml`
est facultative et n'est pas nécessaire au fonctionnement Grafana Cloud.
