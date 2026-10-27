# 08 · Custom instructions: control what is remembered

By default mem0 keeps every fact that looks useful. That can include a phone number, a health condition, even a card number. **Custom instructions** tell the extraction step what to keep and what to drop.

Set them once for every `add()`:

```python
Memory.from_config({..., "custom_instructions": PRIVACY_INSTRUCTIONS})
```

or per call, as this bot does:

```python
memory.add(messages, user_id=customer, prompt=PRIVACY_INSTRUCTIONS)
```

## Do

1. **Terminal**: start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/08-custom-instructions && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**. Bob sends the same message twice: card number, phone number, wool allergy.
   - **Privacy instructions OFF**: open the `mem0.add` step. The phone number and the allergy are stored.
   - **Privacy instructions ON**: only the order is stored.
3. **App**: read the facts stored with privacy OFF once more. Did mem0 also store something the **bot** said, for example a product claim the bot made up?
4. **Terminal**: check what ScyllaDB holds for Bob.

   ```run,sh
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'bob';"
   ```

## Under the hood

- Custom instructions change only the extraction prompt, so they cost no extra calls.
- Fewer facts means fewer `INSERT`s in ScyllaDB. Compare the CQL count of the two `mem0.add` steps.
- `add()` extracts facts from **both** the customer and the bot. If the bot invents something, it can end up in memory. Instructions like "only remember what the customer states" help.

**Takeaway:** data you never store cannot leak. Decide what memory is for.
