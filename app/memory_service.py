
import re

from sqlalchemy.orm import Session

from app.models import CustomerMemory


def save_memory(
    db: Session,
    customer_id: int,
    memory_key: str,
    memory_value: str,
):
    memory = (
        db.query(CustomerMemory)
        .filter(
            CustomerMemory.customer_id == customer_id,
            CustomerMemory.memory_key == memory_key,
        )
        .first()
    )

    if memory:
        memory.memory_value = memory_value
    else:
        memory = CustomerMemory(
            customer_id=customer_id,
            memory_key=memory_key,
            memory_value=memory_value,
        )
        db.add(memory)

    db.commit()
    db.refresh(memory)

    return memory


def get_memory_value(
    db: Session,
    customer_id: int,
    memory_key: str,
):
    memory = (
        db.query(CustomerMemory)
        .filter(
            CustomerMemory.customer_id == customer_id,
            CustomerMemory.memory_key == memory_key,
        )
        .first()
    )

    if memory:
        return memory.memory_value

    return None


def get_customer_memories(
    db: Session,
    customer_id: int,
):
    return (
        db.query(CustomerMemory)
        .filter(
            CustomerMemory.customer_id == customer_id
        )
        .all()
    )


def delete_memory(
    db: Session,
    customer_id: int,
    memory_key: str,
):
    memory = (
        db.query(CustomerMemory)
        .filter(
            CustomerMemory.customer_id == customer_id,
            CustomerMemory.memory_key == memory_key,
        )
        .first()
    )

    if not memory:
        return False

    db.delete(memory)
    db.commit()

    return True


def extract_name(question: str):
    patterns = [
        r"\bmy name is\s+([A-Za-z][A-Za-z .'-]{0,48})",
        r"\bremember my name as\s+([A-Za-z][A-Za-z .'-]{0,48})",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            question,
            flags=re.IGNORECASE,
        )

        if match:
            name = match.group(1).strip(" .,'")

            # Avoid saving long sentences as a name.
            if len(name.split()) <= 4 and name:
                return name

    return None
