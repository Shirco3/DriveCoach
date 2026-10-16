
# DriveCoach — Driving Lesson Evaluation System

**Developed by:** Shir Ben Dror  
**Email:** shir2861999@gmail.com  
**Role:** Junior Backend & Cloud Engineer — Take-Home Assignment

## Overview

DriveCoach is an event-driven backend application that processes driving lesson telemetry data, calculates driving performance metrics, evaluates lessons using configurable rules, and maintains student progress.

The system is implemented in Python and deployed to AWS using Terraform.

## Architecture

```text
Driving Lesson CSV
        |
        v
Private Amazon S3 Bucket
        |
        v
S3 Event Notification
        |
        v
AWS Lambda (Python 3.12)
        |
        +--> Parse and validate CSV
        +--> Calculate driving metrics
        +--> Evaluate versioned rules
        +--> Save lesson audit records
        +--> Recompute student states
                    |
                    v
             Amazon DynamoDB
             - Lessons Table
             - Students Table
```

## Technology Stack

- Python 3.12 — Backend processing
- Amazon S3 — Lesson CSV storage
- AWS Lambda — Event-driven processing
- Amazon DynamoDB — Lesson records and student states
- Terraform — Infrastructure as Code
- GitHub Actions — Automated testing and deployment configuration
- AWS CloudWatch — Lambda execution logs

## AWS Deployment

The application was successfully deployed and tested in AWS.

| Resource | Value |
|---|---|
| AWS Region | eu-north-1 |
| Lambda Function | drivecoach-processor |
| S3 Bucket | drivecoach-raw-20261016220440220100000001 |
| Lessons Table | drivecoach-lessons |
| Students Table | drivecoach-students |

### Deployment Verification

The deployed application was tested by uploading lesson `L-1001.csv` to S3.

The upload triggered AWS Lambda, which processed the lesson and saved the following result to DynamoDB:

- Lesson ID: L-1001
- Result: PASS
- Lesson Score: 90.44

The complete sample dataset was subsequently uploaded.

The dataset contains 16 CSV files representing 15 unique lesson IDs, because one lesson appears again as a retry.

The final student states in DynamoDB were compared with the local processing results and matched.

### Live Invocation

The system is triggered by uploading a lesson CSV to the S3 bucket under the `incoming/` prefix.

Example:

```powershell
aws s3 cp "sample_data/lessons/CAR-01/2026-10-05/L-1001.csv" "s3://drivecoach-raw-20261016220440220100000001/incoming/L-1001.csv" --region eu-north-1
```

The application does not expose a public HTTP endpoint. AWS permissions are required to upload and inspect data.

## Deployment Instructions

Requirements:

- Python 3.12
- AWS CLI
- Terraform 1.5 or newer
- AWS credentials with suitable permissions

Run from the repository root:

```bash
aws sts get-caller-identity

terraform -chdir=terraform init
terraform -chdir=terraform validate
terraform -chdir=terraform plan
terraform -chdir=terraform apply
terraform -chdir=terraform output
```

The Terraform configuration uses the AWS region `eu-north-1`.

After deployment, upload lesson CSV files to the S3 bucket returned by Terraform.

To remove the infrastructure after the evaluation period:

```bash
terraform -chdir=terraform destroy
```

The deployed AWS resources should remain available for at least 72 hours after submission.

## Local Execution and Testing

Run the unit tests:

```bash
python -m unittest discover -s tests -v
```

Run local processing:

```bash
python src/main.py
```

The application generates `results.json` with lesson evaluations and final student states.

All four included unit tests passed during local verification.

## Lesson Evaluation Results

The following results were generated locally from the provided dataset.

| Lesson ID | Student ID | Result |
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

The duplicate file `L-1007_retry1.csv` uses the same lesson ID as `L-1007.csv` and does not create an additional unique lesson record.

## Final Student States

The following states were calculated locally and compared with the deployed DynamoDB data.

| Student | Program | Completed Lessons | Reviews | Status | Final Score |
|---|---|---:|---:|---|---:|
| S-001 | STANDARD | 12 | 0 | COMPLETED | 89.73 |
| S-002 | STANDARD | 5 | 2 | ACTIVE | — |
| S-003 | EXTENDED | 7 | 0 | ACTIVE | — |
| S-004 | EXTENDED | 10 | 2 | INSTRUCTOR_REVIEW | — |

## Rules and Student State Management

Lesson evaluations are performed using the bundled `rules_v1.json` configuration.

Supported evaluation results:

- PASS
- REVIEW
- FAIL
- INVALID

Student progression depends on the current training program, lesson type, review count, and evaluation result.

After a lesson is stored, the application retrieves existing lessons, sorts them by `started_at`, and recomputes student states from the initial student dataset.

Duplicate lesson IDs are stored as one lesson record. A duplicate ID with a conflicting start timestamp raises an error.

Both the original lesson evaluation and the result used for student-state transitions are recorded.

## Security

The infrastructure uses:

- Private Amazon S3 storage
- S3 server-side encryption
- IAM permissions scoped to the application
- DynamoDB for persistent state
- CloudWatch execution logs

AWS credentials and local Terraform state files must not be committed to GitHub.

The repository is private.

## CI/CD

The project includes a GitHub Actions workflow:

`.github/workflows/ci.yml`

The workflow performs automated Python unit tests when code is pushed to the `main` branch.

The deployment job is configured to use AWS OIDC authentication and requires the `AWS_ROLE_ARN` GitHub Actions variable.

Automated deployment through GitHub Actions has not been verified end to end.

The working AWS environment was deployed manually using Terraform.

## Assumptions and Limitations

- The supplied 16 CSV files represent 15 unique lesson IDs.
- Duplicate lesson IDs are processed as a single stored lesson.
- Lessons are replayed chronologically according to their start time.
- Concurrent Lambda executions may cause competing student-state updates. Additional synchronization would be required for production use.
- Versioned rules are bundled with the Lambda deployment and currently require redeployment when changed.
- The final score is based on available passed regular lessons; historical lessons without telemetry are not assigned invented scores.
- Some initial student-state numeric fields are represented as strings rather than numeric values.
- The implementation does not expose a public read API.
- A dead-letter queue, advanced monitoring, and production-grade concurrency control are not included.
- AWS resources may incur charges while deployed.

## Improvements With Additional Time

The next improvements would include:

- Per-student ordered processing using SQS
- Stronger idempotency and transactional state updates
- Dead-letter queue and replay support
- CloudWatch monitoring and alarms
- Authenticated read API
- Externally managed, versioned rule configurations
- Additional integration tests
- Fully verified automated deployment through GitHub Actions

## Cleanup

Keep the deployed infrastructure running for at least 72 hours after submitting the assignment.

After the evaluation period, destroy the infrastructure:

```bash
terraform -chdir=terraform destroy
```

Verify that AWS resources were removed and continue monitoring the account for unexpected charges.
