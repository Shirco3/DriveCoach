# Shir Ben Dror — DriveCoach
**Junior Backend & Cloud Engineer — Take-Home Assignment**

## Overview

DriveCoach is an event-driven backend application that processes driving lesson telemetry, calculates driving performance metrics, evaluates lessons using versioned rules, and maintains student progress.

The solution is implemented in Python and deployed to AWS using Terraform.

## Architecture

```text
Lesson CSV
    |
    v
Private S3 Bucket (incoming/)
    |
    v
S3 Event Notification
    |
    v
AWS Lambda (Python 3.12)
    |
    +--> Parse and validate CSV
    +--> Calculate lesson metrics
    +--> Evaluate versioned rules
    +--> Persist lesson evaluation and audit information
    +--> Replay lessons in chronological order
               |
               v
       DynamoDB Student States
```

## AWS Deployment

The application was successfully deployed and tested in AWS.

| Resource | Value |
|---|---|
| AWS Region | eu-north-1 |
| Lambda Function | drivecoach-processor |
| S3 Bucket | drivecoach-raw-20261016220440220100000001 |
| Lessons Table | drivecoach-lessons |
| Students Table | drivecoach-students |

**Verified:** Uploading lesson `L-1001.csv` to S3 triggered AWS Lambda, which processed the lesson and stored a `PASS` result with a score of `90.44` in DynamoDB.

The full sample dataset was subsequently uploaded. DynamoDB contained 15 unique lesson records from 16 input CSV files, including a repeated lesson ID.

The final student states in AWS were compared against the local run and matched.

There is no public HTTP API in this implementation. The deployed application is invoked through authenticated S3 uploads.

## Deployment Instructions

Requirements: Python 3.12, AWS CLI, Terraform, and valid AWS credentials.

```bash
aws sts get-caller-identity
terraform -chdir=terraform init
terraform -chdir=terraform validate
terraform -chdir=terraform plan
terraform -chdir=terraform apply
terraform -chdir=terraform output
```

The Terraform configuration defaults to `eu-north-1`.

To invoke the deployed system, upload a lesson CSV:

```bash
aws s3 cp sample_data/lessons/CAR-01/2026-10-05/L-1001.csv \
s3://drivecoach-raw-20261016220440220100000001/incoming/L-1001.csv \
--region eu-north-1
```

To inspect a processed lesson or student state, use the AWS Console or AWS CLI to read the relevant DynamoDB table.

## Local Testing

```bash
python -m unittest discover -s tests -v
python src/main.py
```

The local application produces `results.json`, including lesson evaluations and final student states.

## Lesson Evaluation Results

The following results were generated locally using the supplied dataset.

| Lesson | Student | Result |
|---|---|---|
| L-1001 | S-001 | PASS |
| L-1004 | S-002 | PASS |
| L-1009 | S-003 | REVIEW |
| L-1012 | S-004 | REVIEW |
| L-1002 | S-001 | PASS |
| L-1005 | S-002 | REVIEW |
| L-1010 | S-003 | FAIL |
| L-1013 | S-004 | PASS |
| L-1006 | S-002 | PASS |
| L-1003 | S-001 | PASS |
| L-1007 | S-002 | REVIEW |
| L-1014 | S-004 | INVALID |
| L-1008 | S-002 | PASS |
| L-1011 | S-003 | PASS |
| L-1015 | S-004 | FAIL |

The input contains 16 CSV files and 15 unique lesson IDs because `L-1007_retry1.csv` references the same lesson ID as `L-1007.csv`.

## Final Student States

These final states were verified against DynamoDB.

| Student | Program | Completed | Reviews | Status | Final Score |
|---|---|---:|---:|---|---:|
| S-001 | STANDARD | 12 | 0 | COMPLETED | 89.73 |
| S-002 | STANDARD | 5 | 2 | ACTIVE | — |
| S-003 | EXTENDED | 7 | 0 | ACTIVE | — |
| S-004 | EXTENDED | 10 | 2 | INSTRUCTOR_REVIEW | — |

## Rules and State Management

Lessons are evaluated using the bundled `rules_v1.json` configuration.

The application supports PASS, REVIEW, FAIL and INVALID evaluations. Student progression depends on the current program, lesson type, review count and lesson evaluation.

During each processing invocation, stored lessons are sorted by `started_at` and student states are recomputed from the initial dataset.

## Security

The infrastructure uses private S3 storage, server-side encryption, IAM permissions scoped to the application, and DynamoDB for persistent state.

AWS credentials are not included in the repository.

Terraform state files, temporary local files and credentials must not be committed to GitHub.

## CI/CD

The repository contains a GitHub Actions workflow, `.github/workflows/ci.yml`.

- CI runs Python unit tests on pushes to `main`.
- CD defines a Terraform deployment job.
- Automatic deployment requires an appropriately configured AWS OIDC role and the GitHub Actions variable `AWS_ROLE_ARN`.
- Automated CD has not yet been verified end to end.

The AWS deployment was performed manually using Terraform.

## Assumptions and Limitations

- Repeated lesson IDs are stored as one lesson record.
- Conflicting timestamps for the same lesson ID cause an error.
- Historical lessons are replayed in chronological order.
- Concurrent Lambda executions can still race when updating shared state. A per-student queue, transactional versioning or another serialization mechanism is recommended for production.
- Some existing student-state numeric values are represented as strings; numeric normalization would improve consistency.
- Rules are bundled into the deployment artifact and require redeployment to change.
- The implementation does not provide an authenticated read API, dead-letter queue or full production monitoring.
- `final_score` uses the available regular passed lessons rather than inventing scores for lessons completed before the sample dataset.

## Improvements With Additional Time

I would prioritize stronger concurrency control, transactional state updates, an SQS dead-letter queue, integration tests, CloudWatch alarms, an authenticated read API, externally managed rule versions and a verified GitHub Actions deployment pipeline.

## Cleanup

The AWS deployment should remain available for the requested 72-hour evaluation period following submission.

After that period, resources can be removed with:

```bash
terraform -chdir=terraform destroy
```

AWS resources may incur charges while running. Budget monitoring should remain enabled until all resources are removed.