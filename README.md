# Agent Séance

Summon the ghost of a failed AI-agent run with local Gemma (Ollama). A deterministic coroner rules on the cause of death, the ghost testifies citing [step N], and uncited claims are struck from the record.

```bash
ollama pull gemma3:4b
python3 seance.py traces/*.json --html ofrenda.html
```

Trace format: `{"name","task","steps":[{"type":"tool_call|tool_result|final","tool","args|content","error"?}]}`

MIT licence. Built for DEV Hacktoberfest 2026 Week 4 by Vasu Bansal.
