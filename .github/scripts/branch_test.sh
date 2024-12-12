./.github/scripts/create_signature_files.sh
find . -type f -name $(cd droid/droid-results/custom_home/signature_files && ls) -exec cp signature-file.xml {} \;
find . -type f -name $(cd droid/droid-results/custom_home/container_sigs && ls) -exec cp container-signature-file.xml {} \;
sed -i 's/assertThat(api\.getBinarySignatureVersion(), is("[0-9]\{3\}"));/assertThat(api.getBinarySignatureVersion(), is("119"));/' droid/droid-api/src/test/java/uk/gov/nationalarchives/droid/internal/api/DroidAPITest.java
wget -q $(curl https://api.github.com/repos/richardlehane/builder/releases/latest | jq -r '.assets[0].browser_download_url')
unzip -q pronom.zip
rm -rf droid/droid-core/test-skeletons/fmt droid/droid-core/test-skeletons/x-fmt
mv skeleton-suite/x-fmt/x-fmt-182-signature-id-771.qxd skeleton-suite/fmt/fmt-2007-signature-id-771.qxd
mv skeleton-suite/x-fmt/x-fmt-182-signature-id-772.qxd skeleton-suite/fmt/fmt-2007-signature-id-772.qxd
rm skeleton-suite/x-fmt/x-fmt-223-signature-id-337.cel
cp -r skeleton-suite/fmt droid/droid-core/test-skeletons
cp -r skeleton-suite/x-fmt droid/droid-core/test-skeletons
mkdir -p submissions/files
if [ ! -z "$( ls -A 'submissions/files' )" ]; then
   mv submissions/files/* droid/droid-core/test-skeletons/fmt
fi
cd droid
mvn -q clean test