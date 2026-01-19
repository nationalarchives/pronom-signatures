# PRONOM signatures

This repository contains a record of all PRONOM signatures in JSON format. This is used to build the PRONOM signature file and container signature files.

This repository can be used to submit new signatures to PRONOM.

## Submitting new signatures

[Create a fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) of this repository.

Check out your fork locally.

Create a directory called submissions in the root of the project.

Add a json file with the details of the new signature in the submissions directory. The name of the file doesn't matter. The following fields are mandatory.

```json
{
  "formatName": "A test PRONOM file",
  "formatDescription": "This is a test file",
  "internalSignatures": [
    {
      "positionType": "Absolute from BOF",
      "offset": 0,
      "maxOffset": 0,
      "byteSequences": [
        {
          "positionType": "Absolute from EOF",
          "offset": 0,
          "maxOffset": 1024,
          "byteSequence": "5445535450524F4E4F4D",
          "endianness": null
        }
      ],
      "name": "PRONOM test",
      "note": "A PRONOM test signature"
    }
  ]
}

```

There are many other fields you can optionally add which are specified in the [format JSON schema file](/format_schema.json)

Optionally, you can add test files which will be used to check the signature matches those files. To do this, create a directory inside submissions called `files` and place any test files in there. If you aren't including test files, you don't need to create a directory.

So the final structure will look like:
```bash
└── submissions
    ├── files
    │   └── test.pronomtest
    └── submission.json
```

Commit and push this to your forked repository and then [create a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork) to merge back to this repository.

There are tests which will build your submission into a temporary signature file and run the DROID tests against it. If these pass then a member of staff at TNA will review and eventually merge the pull request. 

The tests will also generate a signature file and container signature file which you can download to test for yourself. There is a guide to downloading artifacts [here](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/downloading-workflow-artifacts).

Merging the pull request won't immediately deploy a new version. At some point, a TNA staff member will raise a pull request to merge all the latest submissions into the main branch and once this is merged, a new release will be generated.

