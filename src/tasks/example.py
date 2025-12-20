"""
Example Celery Tasks
Background job processing examples
Source: https://docs.celeryq.dev/en/stable/userguide/tasks.html
Verified: 2025-11-14
"""

import time

from src.utils.celery_app import celery_app
from src.utils.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="example.hello")
def hello_task(name: str) -> str:
    """
    Simple example task.

    Args:
        name: Name to greet

    Returns:
        Greeting message

    Evidence: Basic Celery task pattern
    Source: https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html
    Verified: 2025-11-14
    """
    logger.info(f"Hello task started for: {name}")
    result = f"Hello, {name}!"
    logger.info(f"Hello task completed: {result}")
    return result


@celery_app.task(name="example.long_running", bind=True)
def long_running_task(self, duration: int = 10) -> dict:
    """
    Long-running task with progress updates.

    Args:
        self: Task instance (bind=True required)
        duration: Task duration in seconds

    Returns:
        Task result dictionary

    Evidence: Task progress tracking
    Source: https://docs.celeryq.dev/en/stable/userguide/tasks.html#custom-task-classes
    Verified: 2025-11-14
    """
    logger.info(f"Long running task started: {duration}s")

    for i in range(duration):
        time.sleep(1)
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={"current": i + 1, "total": duration, "percent": ((i + 1) / duration) * 100},
        )

    logger.info("Long running task completed")

    return {"status": "completed", "duration": duration}


@celery_app.task(name="example.process_document")
def process_document_task(document_id: str) -> dict:
    """
    Example document processing task.

    Args:
        document_id: Document UUID

    Returns:
        Processing result

    Evidence: Async document processing pattern
    Source: https://docs.celeryq.dev/en/stable/userguide/calling.html
    Verified: 2025-11-14
    """
    logger.info(f"Processing document: {document_id}")

    # TODO: Implement actual document processing
    # - Load document from database
    # - Generate embeddings
    # - Extract metadata
    # - Update database

    result = {
        "document_id": document_id,
        "status": "processed",
        "message": "Document processing completed successfully",
    }

    logger.info(f"Document processed: {document_id}")

    return result


@celery_app.task(name="example.send_email")
def send_email_task(to: str, subject: str, body: str) -> dict:  # noqa: ARG001
    """
    Example email sending task.

    Args:
        to: Recipient email
        subject: Email subject
        body: Email body

    Returns:
        Send result

    Evidence: Async email sending
    Source: https://docs.celeryq.dev/en/stable/userguide/tasks.html#example
    Verified: 2025-11-14
    """
    logger.info(f"Sending email to: {to}")

    # TODO: Implement actual email sending
    # - Use SMTP configuration from settings
    # - Send email via smtp library
    # - Handle errors and retries

    result = {
        "to": to,
        "subject": subject,
        "status": "sent",
        "message": "Email sent successfully",
    }

    logger.info(f"Email sent to: {to}")

    return result
