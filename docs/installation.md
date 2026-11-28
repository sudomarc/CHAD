# Installation de CHAD

## Compatibilité

CHAD nécessite Python 3.11 ou supérieur.

Le paquet Debian est **architecture indépendante** (`Architecture: all`) : il contient du code Python et utilise l'interpréteur système `/usr/bin/python3`.

Le dépôt APT actuellement publié ne fournit toutefois qu'un index **amd64**. Vérifie l'architecture native avant de choisir cette méthode :

```bash
dpkg --print-architecture
python3 --version
```

- `amd64` : le dépôt APT peut être utilisé.
- `i386` ou une autre architecture : utilise l'installation directe du paquet Debian, sous réserve d'avoir Python 3.11+.

## Méthode recommandée — paquet Debian direct

Cette méthode installe le paquet de la version publiée sans dépendre de l'index du dépôt APT CHAD. Elle convient aussi aux systèmes non-amd64 compatibles avec Python 3.11+.

1. Ouvre le [site officiel d'installation](https://sudomarc.github.io/CHAD/) et relève la version affichée.
2. Remplace `0.1.0` ci-dessous par cette version, puis télécharge et installe le paquet :

```bash
VERSION="0.1.0"
curl -fLO "https://sudomarc.github.io/CHAD/downloads/chad_${VERSION}_all.deb"
sudo apt install "./chad_${VERSION}_all.deb"
```

3. Vérifie l'installation :

```bash
chad --version
chad --help
```

APT résout les dépendances du fichier local à partir des dépôts Debian configurés. Cette méthode **n'ajoute pas** le dépôt APT de CHAD : pour mettre à jour CHAD, télécharge et installe le nouveau fichier `.deb` publié sur le site.

## Debian / Ubuntu — dépôt APT signé (amd64)

Le dépôt APT permet de recevoir les mises à jour de CHAD avec le gestionnaire de paquets. Il est actuellement publié pour `amd64` uniquement.

### 1. Vérifier l'architecture

```bash
dpkg --print-architecture
```

Continue avec cette méthode uniquement si la commande affiche `amd64`. Sur `i386` ou une autre architecture, utilise la méthode du paquet Debian direct ci-dessus.

### 2. Importer la clé et ajouter le dépôt

```bash
sudo install -d -m 0755 /usr/share/keyrings
curl -fsSL https://sudomarc.github.io/CHAD/apt/KEY.asc \
  | sudo gpg --dearmor --yes -o /usr/share/keyrings/chad-archive-keyring.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/chad-archive-keyring.gpg] https://sudomarc.github.io/CHAD/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/chad.list
```

### 3. Actualiser et vérifier que le paquet est réellement indexé

```bash
sudo apt update
apt-cache policy chad
```

**Avant d'installer, vérifie que `apt-cache policy chad` affiche une version dans `Candidate`.** Le message `Hit: ... CHAD ... InRelease` confirme seulement que les métadonnées signées du dépôt ont été récupérées ; il ne prouve pas que l'index des paquets a été chargé.

Si `Candidate: (none)` apparaît, ne répète pas simplement `sudo apt install chad`. Suis la section [Dépannage](#depannage) ou installe le paquet Debian direct.

### 4. Installer et mettre à jour

```bash
sudo apt install chad
chad --version
```

Pour mettre à jour une installation APT :

```bash
sudo apt update
sudo apt upgrade chad
```

Pour désinstaller :

```bash
sudo apt remove chad
```

## Installation depuis les sources avec pipx

Utilise cette méthode pour installer la version présente sur Git et isoler CHAD dans son propre environnement Python. Elle nécessite Python 3.11+.

```bash
sudo apt update
sudo apt install pipx python3-venv git
pipx ensurepath
pipx install git+https://github.com/sudomarc/CHAD.git
```

L'interface TUI utilise Textual. Pour installer cette dépendance dans l'environnement pipx :

```bash
pipx inject chad "textual>=8.0"
```

## Premières commandes

```bash
chad --version
chad --help
chad run "Inspecte ce dépôt et résume sa structure"
```

Sans fournisseur configuré, CHAD utilise son fournisseur fictif de test. Pour appeler un vrai modèle, configure un fournisseur dans `chad.toml` et définis la variable d'environnement API correspondante. Ne stocke jamais de clé API dans le dépôt.

## Configuration d'un fournisseur

Exemple de fichier `chad.toml` placé à la racine du workspace :

```toml
[chad]
provider = "openai"
model = "MODEL_ID"
```

Définis ensuite `OPENAI_API_KEY` dans ton environnement. Le nom du modèle dépend du fournisseur et de ton compte.

## Dépannage

### `Unable to locate package chad`

Un dépôt peut répondre avec `InRelease` sans que le paquet soit présent dans l'index APT utilisable par ta machine.

Commence par vérifier :

```bash
dpkg --print-architecture
apt-cache policy chad
grep -Rns 'sudomarc.github.io/CHAD' \
  /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null
```

- Si l'architecture native n'est pas `amd64`, utilise le [paquet Debian direct](#methode-recommandee--paquet-debian-direct).
- Si l'architecture est `amd64` mais que `Candidate` vaut `(none)`, force le renouvellement des seuls index CHAD puis vérifie à nouveau :

```bash
sudo rm -f /var/lib/apt/lists/*sudomarc.github.io*CHAD*
sudo apt update
apt-cache policy chad
```

- Si `Candidate` reste à `(none)`, installe le fichier `.deb` depuis le [site officiel](https://sudomarc.github.io/CHAD/). Le dépôt APT doit être corrigé côté publication ; ne désactive pas `apt-secure`.

Les erreurs provenant d'un autre dépôt (par exemple un dépôt tiers inaccessible) sont distinctes du dépôt CHAD. Ne les confonds pas avec une erreur de signature ou d'index CHAD.

### Autres problèmes

- **Python trop ancien :** CHAD exige Python 3.11+. Vérifie avec `python3 --version`.
- **Signature APT invalide :** vérifie que la clé `KEY.asc` provient du site officiel et que l'horloge système est correcte.
- **Commande `chad tui` indisponible :** installe Textual avec `pipx inject chad "textual>=8.0"`.
- **Le modèle ne répond pas comme attendu :** vérifie le fournisseur, l'identifiant du modèle et la variable d'environnement de la clé API.

Ne désactive jamais la vérification des signatures, n'utilise pas `trusted=yes` et n'ajoute pas de dépôt non signé.

## Publication du dépôt APT (mainteneurs)

Le workflow GitHub Actions construit le paquet Debian et le site. Il publie le dépôt APT uniquement si les secrets suivants sont disponibles :

- `CHAD_APT_GPG_PRIVATE_KEY` : clé privée ASCII-armored dédiée à la signature de l'archive.
- `CHAD_APT_GPG_PASSPHRASE` : facultatif, si la clé privée est protégée par une phrase secrète.

La clé privée ne doit jamais être committée ni affichée dans les logs. La clé publique exportée devient `apt/KEY.asc` sur GitHub Pages.

Dans les paramètres du dépôt, configure GitHub Pages avec **Source: GitHub Actions**.
