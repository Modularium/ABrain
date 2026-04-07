# Agent Roles

ABrain uses simple role labels to control agent behaviour. Every agent profile
specifies a `role` such as `writer`, `critic` or `retriever`.

The session manager attaches agents with a role and an optional priority. The
reasoner can limit voting to selected roles so that, for example, only critics
may approve a result.

Additional flags:

- **priority** – smaller numbers are executed first
- **exclusive** – if set, only this agent contributes to the decision
