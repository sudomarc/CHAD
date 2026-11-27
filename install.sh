#!/usr/bin/env bash
#
# install.sh — Installe CHAD via un dépôt APT local signé (pattern NETWATCH)
#
# Ce script :
#   1. Génère une clé GPG pour signer le dépôt apt local
#   2. Construit un paquet .deb pour CHAD
#   3. Dépose le paquet dans un dépôt apt local (/var/www/html/apt ou /opt/chad/apt)
#   4. Ajoute la source APT et la clé de confiance sur le système
#   5. Installe le paquet chad via apt
#
# Usage : sudo ./install.sh
#
# NOTE : Aucun token ni secret n'est lu depuis ~/.claude/.env. Si ton dépôt
# distant nécessite une authentification, configure-la séparément dans
# /etc/apt/apt.conf.d/ (voir la section "Authentification" plus bas).

set -euo pipefail

ARCH="$(dpkg --print-architecture)"
REPO_DIR="/opt/chad-apt"
POOL_DIR="${REPO_DIR}/pool/main/c/chad"
DISTS_DIR="${REPO_DIR}/dists/stable/main/binary-${ARCH}"
RELEASE_DIR="${REPO_DIR}/dists/stable"
KEYRING_DIR="/usr/share/keyrings"
KEYRING_FILE="${KEYRING_DIR}/chad-archive-keyring.gpg"
SOURCE_LIST="/etc/apt/sources.list.d/chad.list"
GPG_HOME="/tmp/chad-gnupg"
CHAD_VERSION="0.1.0"

echo "[CHAD] Installation de CHAD via dépôt APT local signé…"

# ---------------------------------------------------------------------------
# 0. Prérequis
# ---------------------------------------------------------------------------
need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "[ERREUR] La commande '$1' est requise mais introuvable." >&2
        exit 1
    }
}

for c in dpkg-deb gpg gpg-agent apt apt-get install curl; do
    need_cmd "$c"
done

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERREUR] Ce script doit être exécuté avec sudo." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 1. Générer une clé GPG pour signer le dépôt
# ---------------------------------------------------------------------------
echo "[CHAD] Génération de la clé GPG de signature du dépôt…"
rm -rf "${GPG_HOME}"
mkdir -p "${GPG_HOME}"
chmod 700 "${GPG_HOME}"

cat > "${GPG_HOME}/gpg-batch.conf" <<EOF
%echo Generating CHAD APT signing key
Key-Type: RSA
Key-Length: 2048
Key-Usage: sign
Name-Real: CHAD APT Archive
Name-Email: chad-apt@localhost
Expire-Date: 0
%no-protection
%commit
%echo done
EOF

gpg --batch --homedir "${GPG_HOME}" --generate-key "${GPG_HOME}/gpg-batch.conf"
GPG_FPR="$(gpg --batch --homedir "${GPG_HOME}" --with-colons --list-keys 'CHAD APT Archive' \
    2>/dev/null | awk -F: '/^fpr:/ {print $10; exit}')"

if [ -z "${GPG_FPR}" ]; then
    echo "[ERREUR] Impossible de récupérer l'empreinte de la clé GPG." >&2
    export GNUPGHOME="${GPG_HOME}"
    gpg --list-keys || true
    exit 1
fi

echo "[CHAD] Clé GPG générée : ${GPG_FPR}"

# Exporter la clé publique au format de confiance APT
install -d -m 0755 "${KEYRING_DIR}"
gpg --batch --homedir "${GPG_HOME}" --armor --export "${GPG_FPR}" \
    | gpg --dearmor --yes --output "${KEYRING_FILE}"
chmod 0644 "${KEYRING_FILE}"
chown root:root "${KEYRING_FILE}"

echo "[CHAD] Clé publique installée dans ${KEYRING_FILE}"

# ---------------------------------------------------------------------------
# 2. Construire le paquet .deb pour CHAD
# ---------------------------------------------------------------------------
echo "[CHAD] Construction du paquet Debian…"

DEB_STAGE="$(mktemp -d)"
DEB_DIR="${DEB_STAGE}/chad_${CHAD_VERSION}"
DEB_ARCH_DEB="${DEB_DIR}/DEBIAN"
DEB_OPT="${DEB_DIR}/opt/chad"
DEB_BIN="${DEB_DIR}/usr/bin"

mkdir -p "${DEB_ARCH_DEB}" "${DEB_OPT}" "${DEB_BIN}"

# Copier le projet Python dans /opt/chad (sauf .venv, .git, tests)
cp -a /home/marco/data/DEV/CHAD "${DEB_OPT}/chad"
rm -rf "${DEB_OPT}/chad/.venv" "${DEB_OPT}/chad/.git"

# Créer le binaire wrapper /usr/bin/chad
cat > "${DEB_BIN}/chad" <<'WRAPPER'
#!/usr/bin/env bash
exec /opt/chad/chad/.venv/bin/chad "$@"
WRAPPER
chmod 0755 "${DEB_BIN}/chad"

# Contrôle du paquet .deb
cat > "${DEB_ARCH_DEB}/control" <<EOF
Package: chad
Version: ${CHAD_VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: CHAD maintainers <chad@localhost>
Description: Local-first general-purpose coding agent.
 CHAD is a local-first, general-purpose software engineering agent with a
 Python orchestration layer, a terminal UI, and a provider-neutral model
 gateway. Installed via local APT repository.
Depends: python3 (>= 3.11), python3-venv
EOF

cat > "${DEB_ARCH_DEB}/postinst" <<'EOF'
#!/usr/bin/env bash
set -e
# S'assurer que le venv existe dans /opt/chad (créé au build ou à l'install)
CHAD_ROOT="/opt/chad/chad"
if [ ! -x "${CHAD_ROOT}/.venv/bin/chad" ]; then
    echo "Création de l'environnement virtuel CHAD…"
    python3 -m venv "${CHAD_ROOT}/.venv"
    "${CHAD_ROOT}/.venv/bin/pip" install --quiet -e "${CHAD_ROOT}"
fi
exit 0
EOF
chmod 0755 "${DEB_ARCH_DEB}/postinst"

dpkg-deb --root-owner-group --build "${DEB_DIR}" "${DEB_STAGE}/chad_${CHAD_VERSION}_${ARCH}.deb"
DEB_FILE="${DEB_STAGE}/chad_${CHAD_VERSION}_${ARCH}.deb"
echo "[CHAD] Paquet construit : ${DEB_FILE}"

# ---------------------------------------------------------------------------
# 3. Mettre en place le dépôt apt local
# ---------------------------------------------------------------------------
echo "[CHAD] Mise en place du dépôt apt local…"
rm -rf "${REPO_DIR}"
mkdir -p "${POOL_DIR}" "${DISTS_DIR}"

cp "${DEB_FILE}" "${POOL_DIR}/"

# Générer Packages.gz avec chemins relatifs (requis par apt pour file:)
(cd "${REPO_DIR}" && dpkg-scanpackages --arch "${ARCH}" "pool/main/c/chad" > "${DISTS_DIR}/Packages" 2>/dev/null || true)
gzip -9c "${DISTS_DIR}/Packages" > "${DISTS_DIR}/Packages.gz"

# Générer Release
# Générer les sections de hachage pour le Release (requis par apt)
generate_hash_section() {
    local hash_cmd="$1"
    local section_name="$2"
    echo "${section_name}:"
    for f in "${DISTS_DIR}/Packages" "${DISTS_DIR}/Packages.gz"; do
        local hash_val size_val path_val
        hash_val=$("${hash_cmd}" "${f}" | awk '{print $1}')
        size_val=$(stat -c%s "${f}")
        path_val="${f#${REPO_DIR}/}"
        echo " ${hash_val} ${size_val} ${path_val}"
    done
}

cat > "${RELEASE_DIR}/Release" <<EOF
Origin: CHAD Local
Label: CHAD
Suite: stable
Version: ${CHAD_VERSION}
Codename: stable
Architectures: ${ARCH}
Components: main
Description: Local APT repository for CHAD packages.
Date: $(date -u +"%a, %d %b %Y %H:%M:%S UTC")
Acquire-By-Hash: no
$(generate_hash_section md5sum "MD5Sum")
$(generate_hash_section sha1sum "SHA1")
$(generate_hash_section sha256sum "SHA256")
EOF

# Signer le Release avec la clé GPG
gpg --batch --homedir "${GPG_HOME}" --default-key "${GPG_FPR}" \
    --detach-sign --armor --output "${RELEASE_DIR}/Release.gpg" "${RELEASE_DIR}/Release"
gpg --batch --homedir "${GPG_HOME}" --default-key "${GPG_FPR}" \
    --clearsign --output "${RELEASE_DIR}/InRelease" "${RELEASE_DIR}/Release"

echo "[CHAD] Dépôt apt prêt dans ${REPO_DIR}"

# ---------------------------------------------------------------------------
# 4. Ajouter la source APT et la clé de confiance
# ---------------------------------------------------------------------------
echo "[CHAD] Ajout de la source APT…"
printf '%s\n' "deb [arch=${ARCH} signed-by=${KEYRING_FILE}] file:${REPO_DIR} stable main" \
    | tee "${SOURCE_LIST}" >/dev/null
chown root:root "${SOURCE_LIST}"
chmod 0644 "${SOURCE_LIST}"

# ---------------------------------------------------------------------------
# 5. Installer CHAD via apt
# ---------------------------------------------------------------------------
echo "[CHAD] Mise à jour des index APT et installation de chad…"
apt-get update
apt-get install -y --allow-downgrades chad

echo ""
echo "[CHAD] Installation terminée."
echo "[CHAD] Testez avec : chad --version"
echo "[CHAD] Ou :      chad run \"ton instruction\""
echo ""
echo "[AUTHENTIFICATION] Si vous utilisez un dépôt distant nécessitant un token,"
echo "ajoutez vos credentials dans /etc/apt/apt.conf.d/ (ex: deb.conf) et ne"
echo "stockez jamais de secret dans ce script."

rm -rf "${DEB_STAGE}"
