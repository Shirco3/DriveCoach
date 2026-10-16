# DriveCoach — Junior Backend & Cloud Engineer

**Candidate:** Shir (replace with full legal name before submission)

## Architecture

```text
Lesson CSV -> private encrypted S3 (incoming/) -> S3 notification -> Python Lambda
                                                -> DynamoDB lessons audit table
                                                -> recompute ordered student states -> DynamoDB students
```

This is a time-limited, best-effort implementation. AWS deployment was not verified as part of the prepared package. The read API, DLQ and production-grade ordering are not implemented.

## Deploy / destroy

Requires AWS CLI credentials for your **own account**, Terraform >=1.5, Python 3.12, and an AWS $10 budget alert set in advance. Budget alerts are not spending limits.

```sh
aws sts get-caller-identity
terraform -chdir=terraform init
terraform -chdir=terraform validate
terraform -chdir=terraform apply
terraform -chdir=terraform output raw_bucket
# Upload sample data after apply, from repository root:
# bash scripts/upload_lessons.sh <raw_bucket_value> incoming 1
# Destroy ONLY after 72 hours following submission:
terraform -chdir=terraform destroy
```

**Do not commit state files, keys or credentials.** Local data samples are synthetic but include personal-data-shaped fields; keep repository private. Lambda bundles only IDs/state from students.csv and does not print names, IDs or contact details. AWS credentials must never be sent to a third party.

## Local test

```sh
python -m unittest discover -s tests -v
python src/main.py
```

`results.json` is generated locally (not committed), containing audit records and student final states.

## Required item 8 — Local results (NOT verified in AWS)

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

### Final student states (local)

| Student | Program | Completed | Reviews | Status | Final score |
|---|---|---:|---:|---|---:|
| S-001 | STANDARD | 12 | 0 | COMPLETED | 89.73 |
| S-002 | STANDARD | 5 | 2 | ACTIVE | - |
| S-003 | EXTENDED | 7 | 0 | ACTIVE | - |
| S-004 | EXTENDED | 10 | 2 | INSTRUCTOR_REVIEW | - |

## Assumptions and tradeoffs

- Duplicate uploads with the same `lesson_id` are de-duplicated. Conflicting timestamps for the same ID raise an error.
- All 16 uploaded files correspond to 15 unique lesson IDs; retry is counted once.
- Lessons are evaluated in UTC `started_at` order. Lambda reserved concurrency 1 reduces interleaving; state is replayed after each upload to handle late records. It is not a robust event-sourced distributed design.
- Rules v1 are bundled into the Lambda artifact; changing rules currently requires a new deployment.
- The recorded result of a REVIEW beyond `max_reviews` becomes FAIL for student transitions; both original result and treated result are kept in audit.
- `final_score` uses REGULAR PASS lessons ingested by this system only, as required; earlier completed lessons do not have score data.
- CSV parsing validates headers and metadata, but not all possible corrupt or contradictory measurement patterns.
- Terraform provisions a private S3 bucket, Lambda, DynamoDB tables and three-day log retention. DynamoDB PAY_PER_REQUEST and AWS Lambda/S3 usage may incur costs.
- No read API endpoint is provided, so the submission email should say the AWS S3 bucket and Lambda name rather than claim a live API URL.

## Existing starter kit issues identified

- Public S3 read policy and disabled block-public-access controls.
- Overly permissive IAM `Action: *` and `Resource: *`.
- Hard-coded instructor API key stored as a normal SSM String. Removed rather than deploying unused insecure credentials.
- Upload script includes a repeated file (`L-1007_retry1.csv`); idempotency is required.

## CI/CD

GitHub Actions runs unit tests on main. Deploy runs if GitHub Actions variable `AWS_ROLE_ARN` is configured with a properly scoped AWS OIDC role. Otherwise deployment is intentionally skipped rather than using stored access keys.

## With another week

Implement a proper ordered per-student queue with idempotent transactions, an SQS DLQ/replay mechanism, CloudWatch alarms, an authenticated read API, protected workflow approvals and independent integration tests using a test AWS account. Add changeable rules versions from S3/SSM with effective dates and signed audit entries.
