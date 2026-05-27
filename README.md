# AWS Serverless Object Detection Application

## Overview

This project implements a fully serverless image inspection and object detection system on AWS for a manufacturing company. The solution automates the manual widget inspection process using AWS Rekognition and event-driven architecture best practices.

The application detects objects in uploaded images, stores inspection results, sends notifications to the Quality Control team, and archives inspection data for compliance purposes.

---

# Project Objectives

The objective of this project is to:

* Automate the widget inspection process
* Eliminate manual image analysis
* Implement a fully serverless AWS architecture
* Detect required objects using AWS Rekognition
* Store inspection results for compliance
* Monitor and secure the solution using AWS services

---

# AWS Services Used

| Service            | Purpose                                             |
| ------------------ | --------------------------------------------------- |
| Amazon S3          | Store uploaded widget images and inspection results |
| AWS Lambda         | Process uploaded images and trigger automation      |
| Amazon Rekognition | Perform object detection and image analysis         |
| Amazon SNS         | Send inspection notifications to Quality Control    |
| Amazon SQS         | Queue image processing events                       |
| Amazon CloudWatch  | Monitoring, logging, and application metrics        |
| AWS IAM            | Security roles and permissions management           |

---

# Solution Architecture

## Workflow

1. A worker uploads a widget image to an S3 bucket.
2. The S3 upload event triggers an SQS message.
3. AWS Lambda reads the SQS event.
4. Lambda extracts image metadata and calls Amazon Rekognition.
5. Rekognition analyzes the image and detects labels/objects.
6. Inspection results are generated automatically.
7. Results are stored in the “inspected” folder in S3.
8. SNS sends a notification to the Quality Control team.
9. CloudWatch logs all processing events for monitoring and troubleshooting.

---

# Features

* Fully serverless implementation
* Event-driven architecture
* Automated image recognition
* Scalable and highly available
* Centralized monitoring and logging
* Secure IAM-based access control
* Long-term compliance storage support

---

# Security Implementation

The application follows AWS security best practices:

* IAM roles with least privilege access
* Secure S3 bucket permissions
* Lambda execution role restrictions
* CloudWatch monitoring enabled
* Controlled SNS/SQS permissions

---

# Monitoring

Amazon CloudWatch is used for:

* Lambda execution logs
* Error monitoring
* Invocation tracking
* Performance metrics
* Troubleshooting and debugging

---

# Testing and Demonstration

The application was tested using sample widget images uploaded into the S3 bucket.

The successful test demonstrates:

* Automatic event triggering
* Rekognition object detection
* Lambda execution
* Notification delivery
* Inspection result storage

---

# Sample Lambda Workflow

```python
import json
import boto3

def lambda_handler(event, context):

    for record in event['Records']:

        jsonmaybe = (record["body"])
        jsonmaybe = json.loads(jsonmaybe)

        bucket_name = jsonmaybe["Records"][0]["s3"]["bucket"]["name"]
        key = jsonmaybe["Records"][0]["s3"]["object"]["key"]

        print(bucket_name)
        print(key)
```

---

# Business Benefits

* Reduces manual inspection effort
* Improves manufacturing quality assurance
* Faster inspection processing
* Improved operational efficiency
* Better compliance tracking
* Reduced human error

---

# Future Enhancements

* Custom Rekognition models
* Real-time dashboard integration
* Defect classification system
* API Gateway integration
* DynamoDB metadata storage
* CI/CD deployment automation

---

# Team Members

* Add team member names here

---

# References

AWS Rekognition Documentation
https://docs.aws.amazon.com/rekognition/latest/dg/labels-detect-labels-image.html

AWS Lambda Documentation
https://docs.aws.amazon.com/lambda/

AWS Architecture Icons
https://aws.amazon.com/architecture/icons/

---

# License

This project was developed for educational purposes as part of a Cloud Computing course project.
