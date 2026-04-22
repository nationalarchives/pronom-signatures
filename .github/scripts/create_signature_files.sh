set -e
rm -rf droid-bin
mkdir droid-bin
cd droid-bin
wget -q $(curl https://api.github.com/repos/digital-preservation/droid/releases/tags/6.9.12 | jq -r '.assets[] | select(.name | contains("with-jre") | not) | .browser_download_url')
echo "c385e39eacd9ae6fb3b37dd79d90f361d5ffaa267a3de09f5ad21956a84ae1c8 droid-binary-6.9.12-bin.zip" | sha256sum -c
unzip -q droid-binary-6.9.12-bin.zip
cd ..
python .github/scripts/add_submission_to_signatures.py $1
python .github/scripts/generate_signature_files.py "$PWD/droid-bin"
