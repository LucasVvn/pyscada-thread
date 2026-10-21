# Tester le plugin dans PyScada (sans capteur)

Prérequis : `migrate thread` passé et services relancés (`pyscada-dev.sh restart` affiche deux fois `active`).

## 1. Lancer le nœud simulé

Dans un terminal, à laisser ouvert :

```bash
/home/pyscada/.venv/bin/python -m pyscada.thread.simulator --bind ::1 --port 5683
```

Ressources : `/temperature` (texte, 18 à 26 °C), `/co2` (texte, 400 à 1500 ppm), `/mesures` (JSON `{"temperature": …, "co2": …, "humidite": 48}`), `/relais` (GET/PUT `0`/`1`). Température et CO2 changent à chaque lecture : la courbe se remplit.

Vérification dans un autre terminal :

```bash
/home/pyscada/.venv/bin/aiocoap-client 'coap://[::1]:5683/temperature'
```

## 2. Mode interrogation (polling)

Admin PyScada (http://localhost:8080/admin) > **Devices** > Ajouter :

| Champ | Valeur |
|---|---|
| Short name | `noeud-simule` |
| Protocol | `thread` |
| Polling interval | `10` (secondes) |
| Active | coché |
| Bloc *Thread device* : IPv6 address | `::1` |
| Port | `5683` |
| Timeout / Retries / Mode | `5` / `2` / `Polling` |

Enregistrer, puis **Variables** > Ajouter :

| Champ | Valeur |
|---|---|
| Name | `SimuTemperature` |
| Device | `noeud-simule` |
| Unit | `°C` (à créer si absente) |
| Value class | `FLOAT32` |
| Active | coché |
| Bloc *Thread variable* : Resource | `/temperature` |
| Payload format | `Plain text` |

Pour l'écriture, une 2e variable `SimuRelais` : value class `BOOLEAN`, **Writeable** coché, resource `/relais`.

Raccourci : `examples/noeud_simule.py` crée d'un coup ce device, les variables `SimuTemperature`, `SimuCO2` (resource `/co2`, unité `ppm`) et `SimuRelais`, ainsi qu'une vue **Thread** de l'IHM avec un graphique température + CO2 :

```bash
cd /var/www/pyscada/PyScadaServer && sudo -u pyscada /home/pyscada/.venv/bin/python manage.py shell < ~/Documents/pyscada-thread/examples/noeud_simule.py
```

Puis relancer pour que le démon charge le device :

```bash
bash ~/Documents/pyscada-dev/pyscada-dev.sh restart
```

## 3. Voir les valeurs

- Logs : `journalctl -u pyscada -n 50` doit montrer `pyscada.thread` et `Connected to device : noeud-simule`.
- IHM : avec le raccourci, ouvrir la vue **Thread** depuis l'accueil de l'IHM (http://localhost:8080). À la main : admin > HMI > **Charts** > ajouter un graphique avec `SimuTemperature` et `SimuCO2`, le mettre dans une page via un **Widget**, et ajouter la page à une **View**.
- Écriture : un widget *Control item* sur `SimuRelais` dans l'IHM ; le terminal du simulateur ne log rien, mais `aiocoap-client 'coap://[::1]:5683/relais'` doit renvoyer la nouvelle valeur.
- Panne : arrêter le simulateur (Ctrl+C) → un seul message « not accessible » dans les logs ; le relancer → « Connected ».

## 4. Mode push

Créer un 2e device `noeud-push` : protocole `thread`, polling interval `5`, IPv6 `::1`, **Mode `Push`**, **Listen port `5684`** (pas 5683, déjà pris par le simulateur), heartbeat timeout `120` si on veut tester l'alerte. Une variable `PushTemperature` sur ce device, resource `/temperature`. Relancer (`pyscada-dev.sh restart`).

Envoyer une mesure comme le ferait le capteur :

```bash
/home/pyscada/.venv/bin/aiocoap-client -m POST --payload 22.5 'coap://[::1]:5684/temperature'
```

Réponse attendue : `2.04 Changed`. La valeur est enregistrée au passage suivant du démon (≤ 5 s). Sans envoi pendant 120 s : message « silent node » dans les logs.
