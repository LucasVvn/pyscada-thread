# pyscada-thread

Plugin [PyScada](https://github.com/pyscada/PyScada) qui ajoute le protocole **Thread** : PyScada lit et pilote des capteurs et actionneurs Thread en **CoAP sur UDP/IPv6**, à travers une passerelle OpenThread Border Router.

- Protocole `thread`, `PROTOCOL_ID = 30`
- Lecture par interrogation (`GET`) ou réception des envois du capteur (mode push, `POST`/`PUT`)
- Écriture sur un actionneur (`PUT`)
- Délai d'attente, tentatives, alerte « capteur injoignable » ou « capteur muet »
- Client et serveur CoAP : [aiocoap](https://aiocoap.readthedocs.io)

## Installation sur le serveur PyScada

Les commandes avec `sudo` sont à taper soi-même dans un terminal.

1. Installer la dépendance `aiocoap` dans le venv du service (le script d'installation utilise `--no-deps`) :
   ```bash
   sudo -u pyscada /home/pyscada/.venv/bin/pip install "aiocoap>=0.4.7"
   ```
2. Installer le plugin en mode éditable et relancer les services :
   ```bash
   bash ~/Documents/pyscada-dev/pyscada-dev.sh install ~/Documents/pyscada-thread
   ```
3. Créer les tables et le protocole `thread` :
   ```bash
   cd /var/www/pyscada/PyScadaServer && sudo -u pyscada /home/pyscada/.venv/bin/python manage.py migrate thread
   ```
4. Relancer pour que le démon charge le worker Thread :
   ```bash
   bash ~/Documents/pyscada-dev/pyscada-dev.sh restart
   ```

Le `settings.py` du serveur ajoute automatiquement toute distribution dont le nom contient `pyscada-` : rien à modifier dans `INSTALLED_APPS`.

## Configuration

### Device (Admin > Thread Devices, ou un Device de protocole `thread`)

| Champ | Rôle | Défaut |
|---|---|---|
| `ipv6_address` | adresse IPv6 stable du nœud (préfixe du maillage, pas link-local), ex. `fd12::a1` | |
| `port` | port CoAP du nœud | 5683 |
| `timeout` | délai d'attente d'une réponse, en secondes | 5 |
| `retries` | nouvelles tentatives après un échec | 2 |
| `mode` | `Polling` : PyScada interroge à chaque `polling_interval`. `Push` : le nœud envoie | Polling |
| `listen_port` | mode push : port UDP sur lequel PyScada écoute (un port par device push) | 5683 |
| `heartbeat_timeout` | mode push : secondes sans envoi avant l'alerte « capteur muet » (0 = désactivé) | 0 |

### Variable

| Champ | Rôle |
|---|---|
| `resource` | chemin de la ressource CoAP, ex. `/temperature` |
| `payload_format` | `Plain text` (`21.4`, `1`, `on`) ou `JSON` |
| `json_key` | en JSON : clé de la valeur, clés imbriquées séparées par des espaces (`capteur t`, `liste [0]`) |

Le seuil **`cov_increment`** (« COV ») de la variable PyScada s'applique aussi : une valeur qui varie moins que ce seuil n'est pas stockée (une valeur par heure au minimum).

## Fonctionnement

**Interrogation** : à chaque `polling_interval`, `GET coap://[adresse]:port/ressource` pour chaque variable. Réponse attendue `2.05 Content`. Une réponse `4.xx`/`5.xx` est journalisée et la valeur ignorée. Sans réponse après `retries + 1` tentatives, le nœud est déclaré injoignable (un seul message jusqu'à son retour) et les autres variables du cycle sont sautées.

**Écriture** : `PUT` de la valeur sur la ressource (`1`/`0` pour un booléen, `{"clé": valeur}` en JSON). Réponse attendue `2.04 Changed`, sinon la tâche d'écriture est marquée en échec.

**Push** : PyScada écoute sur `listen_port`. Le nœud envoie `POST` ou `PUT` sur la ressource de la variable. Seuls les envois venant de `ipv6_address` sont acceptés (sinon `4.03`). Réponse `2.04 Changed`, ou `4.00` si la valeur est illisible. Les valeurs sont enregistrées au passage suivant du démon, horodatées à la réception : un `polling_interval` court (quelques secondes) ne coûte rien côté radio.

## Tester sans matériel

Un nœud simulé expose `/temperature` (texte), `/mesures` (JSON) et `/relais` (GET/PUT) :

```bash
python -m pyscada.thread.simulator --bind ::1 --port 5683
```

Device d'exemple qui interroge ce nœud (voir l'en-tête du fichier) : [`examples/noeud_simule.py`](examples/noeud_simule.py).

Vérifier un nœud à la main :
```bash
aiocoap-client coap://[::1]:5683/temperature
```

## Développement

Les tests tournent sur SQLite, sans MariaDB ni le service :

```bash
python3 -m venv .venv
.venv/bin/pip install "django>=5.2,<5.3" numpy h5py pillow python-daemon pytz python-dateutil asgiref monthdelta six concurrent-log-handler scipy channels "aiocoap>=0.4.7"
echo ~/Documents/pyscada > .venv/lib/python3.12/site-packages/pyscada-core-dev.pth
echo ~/Documents/pyscada-thread > .venv/lib/python3.12/site-packages/pyscada-thread-dev.pth
.venv/bin/python manage.py test tests
```

## Structure

```
pyscada/thread/
├── __init__.py      PROTOCOL_ID, parent_process_list
├── apps.py, admin.py, signals.py
├── models.py        ThreadDevice, ThreadVariable
├── worker.py        Process (un process par device)
├── device.py        Device (GenericDevice)
├── devices/         handler : GET, PUT, tentatives, mode push
├── coap.py          client CoAP synchrone (boucle asyncio dans un thread)
├── push.py          serveur CoAP du mode push
├── simulator.py     nœud Thread simulé
└── migrations/
```

## Licence

AGPLv3, comme PyScada.
