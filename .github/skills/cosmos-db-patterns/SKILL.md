---
name: cosmos-db-patterns
description: 'Works with Azure Cosmos DB — containers, partition keys, queries, and storage integration. Use when working with Cosmos DB, designing partition keys, adding containers, or optimizing queries.'
argument-hint: 'Describe the Cosmos DB task (e.g., "add a sessions container", "optimize query by partition key")'
---

## Purpose
Patterns and workflow for working with Azure Cosmos DB in this template.

## When to Use
- Adding a new Cosmos DB container.
- Designing partition key strategies.
- Writing or optimizing queries.
- Connecting app code to Cosmos DB.

## Container Design

### Existing Containers
| Container | Partition Key | Purpose |
|-----------|--------------|---------|
| `messages` | `/session_id` | Chat message storage |
| `sessions` | `/session_id` | Session metadata |

### Adding a New Container

1. **Choose a partition key**:
   - High cardinality (many unique values) — e.g., `userId`, `tenantId`, `sessionId`.
   - Aligned with your most common query filter.
   - Avoid low-cardinality keys (`status`, `type`) — causes hot partitions.
   - Items within a partition share a 20 GB limit. Use hierarchical partition keys for larger datasets.

2. **Add to Terraform** — create a container in `infra/modules/cosmos-db/main.tf`
   or add to the `containers` list in root `main.tf`:
   ```hcl
   { name = "my-container", partition_key_path = "/tenantId" }
   ```

3. **Add config** to `AppSettings`:
   ```python
   cosmos_container_my_data: str = "my-container"
   ```

4. **Implement in storage layer** — follow `CosmosStorage` pattern in `services/storage.py`.

## Query Patterns

### Parameterized Queries (required)
```python
query = "SELECT * FROM c WHERE c.session_id = @session_id"
parameters = [{"name": "@session_id", "value": session_id}]
container.query_items(query=query, parameters=parameters)
```
**Never** use f-strings or string formatting for queries — prevents injection.

### Within-Partition Queries (preferred)
```python
container.query_items(
    query=query,
    parameters=parameters,
    enable_cross_partition_query=False,  # Fast: stays within one partition
)
```

### Cross-Partition Queries (use sparingly)
Set `enable_cross_partition_query=True` only when querying across partitions. Higher RU cost.

## Performance Guidelines
- **Read by ID + partition key**: fastest, use `read_item()` when possible.
- **Query by partition key**: fast, stays within logical partition.
- **Cross-partition query**: slow, fan-out. Design partition keys to minimize these.
- **Session consistency**: default in this template. Allows read-your-own-writes within a session.

## Checklist
- [ ] Partition key is high-cardinality and aligns with query patterns
- [ ] Terraform container definition added
- [ ] Config added to `AppSettings`
- [ ] Queries use parameterized syntax
- [ ] Cross-partition queries avoided where possible
- [ ] Storage implementation follows `CosmosStorage` pattern
