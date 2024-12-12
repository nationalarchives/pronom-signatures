mkdir droid-bin
cd droid-bin
wget -q $(curl https://api.github.com/repos/digital-preservation/droid/releases/latest | jq -r '.assets[] | select(.name | contains("with-jre") | not) | .browser_download_url')
unzip -q droid-binary-*-bin.zip
cd ..
python .github/scripts/add_submission_to_signatures.py $1
python .github/scripts/generate_signature_files.py "$PWD/droid-bin"