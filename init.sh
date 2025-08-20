#!/bin/bash

# Crée manuellement le dossier manquant
mkdir -p /home/container/.local/lib/python3.11/site-packages
# Crée un lien symbolique vers python3 si python n'existe pas déjà
if [ ! -f /usr/local/bin/python ]; then
    ln -s $(which python3) /usr/local/bin/python
fi
# Installe les paquets
pip install --prefix=/home/container/.local -r /home/container/requirements.txt
