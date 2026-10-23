
from app.database import SessionLocal
from app.memory_service import save_memory, get_customer_memories

db = SessionLocal()

try:
    memory = save_memory(
        db=db,
        customer_id=1,
        memory_key="preferred_currency",
        memory_value="INR",
    )

    print("Saved memory:", memory.memory_key, memory.memory_value)

    memories = get_customer_memories(db, customer_id=1)

    print("\nCustomer memories:")
    for item in memories:
        print(item.memory_key, "=", item.memory_value)

finally:
    db.close()
