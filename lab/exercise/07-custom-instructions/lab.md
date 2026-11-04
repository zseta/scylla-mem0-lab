# 07 · Custom instructions: control what is remembered

By default mem0 keeps every fact that looks useful. That can include a phone number or a health condition. **Custom instructions** tell the extraction step what to keep and what to drop.

Set them once for every `add()`:

```python
Memory.from_config({..., "custom_instructions": PRIVACY_INSTRUCTIONS})
```

or per call, as this bot does:

```python
memory.add(messages, user_id=customer, prompt=PRIVACY_INSTRUCTIONS)
```

## Exercise

1. **Terminal**: start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/07-custom-instructions && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**. Erik sends an order with his phone number and a wool allergy. Privacy instructions are OFF.
   - Open the `mem0.add` step. The wool allergy (health data) is stored, often the phone number too.
3. **App**: click **Next ▶**. Nora sends the same message. Privacy instructions are ON.
   - Open the `mem0.add` step. Only the order is stored.
4. **App**: read Erik's facts once more. One of them is something the **bot** said, for example "User was informed that the plushie is wool-free". mem0 remembers the bot's words too, right or wrong.
5. **Terminal**: compare what ScyllaDB holds for Erik and for Nora. Nora's memories from earlier exercises are there too, but no allergy and no phone number.

   ```run,sh
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'erik';"
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'nora';"
   ```

## Under the hood

- Custom instructions change only the extraction prompt, so they cost no extra calls.
- Fewer facts means fewer `INSERT`s in ScyllaDB. Compare the CQL count of the two `mem0.add` steps.
- `add()` extracts facts from **both** the customer and the bot. If the bot invents something, it can end up in memory. Instructions like "only remember what the customer states" help.

**Takeaway:** data you never store cannot leak. Decide what memory is for.
