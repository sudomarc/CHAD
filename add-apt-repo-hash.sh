#!/usr/bin/env bash
# Ajoute les sections de hachage MD5, SHA1, SHA256 à un fichier Release APT
# Usage : ./add-apt-repo-hash.sh Packages Packages.gz

PACKAGES="$1"
PACKAGES_GZ="$2"
RELEASE_FILE="Release"

if [ ! -f "$PACKAGES" ] || [ ! -f "$PACKAGES_GZ" ]; then
    echo "Fichiers Packages introuvables"
    exit 1
fi

# Section MD5Sum
{
    echo "MD5Sum:"
    for f in "$PACKAGES" "$PACKAGES_GZ"; do
        SIZE=$(stat -c%s "$f")
        HASH=$(md5sum "$f" | awk '{print $1}')
        # Chemin relatif par rapport au repo
        REL_PATH="${f#/opt/chad-apt/}"
        echo "  ${HASH}  ${SIZE}  ${REL_PATH}"
    done
} >> "$RELEASE_FILE"

# Section SHA1Sum
{
    echo "SHA1:"
    for f in "$PACKAGES" "$PACKAGES_GZ"; do
        SIZE=$(stat -c%s "$f")
        HASH=$(sha1sum "$f" | awk '{print $1}')
        REL_PATH="${f#/opt/chad-apt/}"
        echo "  ${HASH}  ${SIZE}  ${REL_PATH}"
    done
} >> "$RELEASE_FILE"

# Section SHA256Sum
{
    echo "SHA256Sum:"
    for f in "$PACKAGES" "$PACKAGES_GZ"; do
        SIZE=$(stat -c%s "$f")
        HASH=$(sha256sum "$f" | awk '{print $1}')
        REL_PATH="${f#/opt/chad-apt/}"
        echo "  ${HASH}  ${SIZE}  ${REL_PATH}"
    done
} >> "$RELEASE_FILE"

# Mettre à jour le fichier Release en place
cp "$RELEASE_FILE" /opt/chad-apt/dists/stable/Release