./.github/scripts/create_signature_files.sh
find . -type f -name $(cd droid/droid-results/custom_home/signature_files && ls) -exec cp signature-file.xml {} \;
find . -type f -name $(cd droid/droid-results/custom_home/container_sigs && ls) -exec cp container-signature-file.xml {} \;
sed -i 's/assertThat(api\.getBinarySignatureVersion(), is("[0-9]\{3\}"));/assertThat(api.getBinarySignatureVersion(), is("119"));/' droid/droid-api/src/test/java/uk/gov/nationalarchives/droid/internal/api/DroidAPITest.java
rm droid/droid-core/test-skeletons/x-fmt/x-fmt-223-signature-id-337.cel
mkdir -p submissions/files
if [ ! -z "$( ls -A 'submissions/files' )" ]; then
   mv submissions/files/* droid/droid-core/test-skeletons/fmt
fi
cd droid
AWS_REGION=eu-west-2 AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test mvn -q clean test