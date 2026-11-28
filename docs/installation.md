# Installation de CHAD

## État de distribution

CHAD nécessite Python 3.11 ou supérieur. Le paquet Debian est construit pour être indépendant de l'environnement local de développement et utilise `/usr/bin/python3`.

Le dépôt APT n'est publié que lorsque la clé de signature d'archive persistante est configurée dans les secrets du dépôt GitHub. Le site d'installation indique automatiquement si cette méthode est activée. N'ajoute jamais une source APT non signée et ne désactive pas la vérification des signatures.

## Debian / Ubuntu — dépôt APT signé

Cette section s'applique uniquement lorsque le site affiche le dépôt APT comme disponible.

Importer la clé publique :

```bash
curl -fsSL https://sudomarc.github.io/CHAD/apt/KEY.asc \
  | sudo gpg --dearmor --yes -o /usr/share/keyrings/chad-archive-keyring.gpg
```

Ajouter la source APT :

```bash
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/chad-archive-keyring.gpg] https://sudomarc.github.io/CHAD/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/chad.list
```

Installer et vérifier :

```bash
sudo apt update
sudo apt install chad
chad --version
chad --help
```

Mettre à jour :

```bash
sudo apt update
sudo apt upgrade chad
```

Désinstaller :

```bash
sudo apt remove chad
```

## Installation directe du paquet Debian

Le site fournit un lien vers le paquet `.deb` construit pour la version publiée. Télécharger le fichier indiqué par le site, puis installer le paquet local :

```bash
sudo apt install ./chad_VERSION_all.deb
```

Remplace `VERSION` par la version affichée sur le site. Cette méthode installe un fichier Debian local ; elle ne configure pas de dépôt APT pour les mises à jour futures.

## Installation depuis les sources avec pipx

Pour installer la version Python directement depuis Git :

```bash
sudo apt update
sudo apt install pipx python3-venv git
pipx ensurepath
pipx install git+https://github.com/sudomarc/CHAD.git
```

Pour installer la dépendance optionnelle de l'interface Textual :

```bash
pipx inject chad "textual>=8.0"
```

## Premières commandes

```bash
chad --version
chad --help
chad run "Inspecte ce dépôt et résume sa structure"
```

Le CLI sélectionne le fournisseur fictif si aucun fournisseur n'est configuré. Pour appeler un vrai modèle, configure un fournisseur dans `chad.toml` et définis la variable d'environnement API correspondante. Les clés API ne doivent jamais être écrites dans le dépôt.

## Configuration d'un fournisseur

Exemple de fichier `chad.toml` placé à la racine du workspace :

```toml
[chad]
provider = "openai"
model = "MODEL_ID"
```

Définis ensuite `OPENAI_API_KEY` dans ton environnement. Le nom du modèle dépend du fournisseur et de ton compte.

## Dépannage

- **Python trop ancien :** utilise Debian 12 / Ubuntu 24.04 ou un environnement qui fournit Python 3.11+.
- **Signature APT invalide :** vérifie que tu as importé le fichier `KEY.asc` correspondant au dépôt actuel et que l'horloge système est correcte.
- **Paquet introuvable :** exécute `sudo apt update` puis vérifie le contenu de `/etc/apt/sources.list.d/chad.list`.
- **Commande `chad tui` indisponible :** installe l'extra Textual avec la méthode pipx décrite ci-dessus.
- **Le modèle ne répond pas comme attendu :** vérifie le fournisseur, le modèle et la variable d'environnement de la clé API.

## Publication du dépôt APT (mainteneurs)

Le workflow GitHub Actions construit toujours le paquet et le site. Il ne publie le dépôt APT que si les secrets suivants sont disponibles :

- `CHAD_APT_GPG_PRIVATE_KEY` : clé privée ASCII-armored dédiée à la signature de l'archive.
- `CHAD_APT_GPG_PASSPHRASE` : facultatif, si la clé privée est protégée par une phrase secrète.

La clé privée ne doit jamais être committée ni affichée dans les logs. La clé publique exportée devient `apt/KEY.asc` sur GitHub Pages.

Dans les paramètres du dépôt, configure également GitHub Pages avec **Source: GitHub Actions** avant le premier déploiement par ce workflow.
