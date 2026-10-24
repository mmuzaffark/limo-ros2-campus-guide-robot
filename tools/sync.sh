#!/bin/bash
# Copy the working scripts from ~ into the repo (run before each commit)
cd ~/limo_ws
for f in ~/*.sh ~/*.py; do cp "$f" tools/; done
cp ~/clips/*.wav clips/ 2>/dev/null
echo "synced $(ls tools | wc -l) tool files, $(ls clips | wc -l) clips"
