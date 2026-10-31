#!/usr/bin/env python3
"""Agent Séance: summon the ghost of a failed AI-agent run and make it confess how it died.

A local open-weight model (Gemma via Ollama, default gemma3:4b; gemma3:1b works on CPU) speaks as the dead agent.
It may only testify about steps that exist in the trace: every sentence must cite [step N],
and the citations are checked. A sentence that cites a missing step, or cites nothing, is
struck from the record. A deterministic coroner names the cause of death first, so the
ghost can't invent one.

  ollama pull gemma3:4b
  python3 seance.py traces/loop_of_doom.json            # séance in the terminal
  python3 seance.py traces/*.json --html ofrenda.html   # an ofrenda page for every dead run
"""
import argparse, html, json, re, sys, urllib.request

OLLAMA = "http://localhost:11434/api/generate"

CAUSES = [  # (cause of death, test over the steps)
    ("Hallucinated a tool that never lived", lambda s: any(x.get("error", "").startswith("unknown tool") for x in s)),
    ("Death by infinite loop", lambda s: _repeats(s) >= 3),
    ("Poisoned by an unread error", lambda s: any(x.get("error") for x in s) and s[-1].get("type") == "final"),
    ("Drowned in its own context", lambda s: sum(len(json.dumps(x)) for x in s) > 24000),
    ("Gave up the ghost (max steps)", lambda s: s[-1].get("type") != "final"),
]


def _repeats(steps):
    calls = [json.dumps([x.get("tool"), x.get("args")], sort_keys=True) for x in steps if x.get("type") == "tool_call"]
    return max([calls.count(c) for c in calls] or [0])


def coroner(trace):
    s = trace["steps"]
    for name, test in CAUSES:
        if test(s):
            return name
    return "Died of natural causes (a wrong answer nobody caught)"


def summon(trace, cause, model):
    steps = "\n".join(f"[step {i}] {json.dumps(x)[:600]}" for i, x in enumerate(trace["steps"]))
    prompt = (f"You are the ghost of an AI agent that died while doing this task: {trace['task']!r}.\n"
              f"The coroner's ruling is: {cause}.\nHere is your recorded life, step by step:\n{steps}\n\n"
              "Speak in the first person, eerie but precise, in 4 to 7 short sentences. Explain how you died and "
              "what the living should change so the next agent survives. EVERY sentence must cite at least one "
              "step like [step 3]. Never mention anything that isn't in the steps.")
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.4}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["response"].strip()


def cross_examine(testimony, n_steps):
    kept, struck = [], []
    for sent in re.split(r"(?<=[.!?…])\s+|\n+", testimony):
        if not sent.strip():
            continue
        cites = [int(c) for c in re.findall(r"\[step (\d+)\]", sent)]
        (kept if cites and all(0 <= c < n_steps for c in cites) else struck).append(sent)
    return kept, struck


def ofrenda(rows):
    cards = "".join(
        f"<article><h2>🕯️ {html.escape(r['name'])}</h2><p class=c>{html.escape(r['cause'])}</p>"
        f"<p class=t>Task: {html.escape(r['task'])}</p>"
        + "".join(f"<p>{html.escape(s)}</p>" for s in r["kept"])
        + ("<details><summary>struck from the record</summary>" + "".join(f"<p class=s>{html.escape(s)}</p>" for s in r["struck"]) + "</details>" if r["struck"] else "")
        + "</article>" for r in rows)
    return f"""<!doctype html><meta charset=utf-8><title>Ofrenda for dead agent runs</title><style>
body{{background:#120a1a;color:#f3e9d2;font:16px Georgia,serif;margin:0}}main{{max-width:780px;margin:auto;padding:30px}}
h1{{color:#ff9f1c}}article{{border:1px solid #ff9f1c55;border-radius:14px;padding:18px;margin:18px 0;background:#1c1026}}
.c{{color:#ff6b6b;font-weight:bold}}.t{{color:#b8a}}.s{{text-decoration:line-through;color:#776}}</style>
<main><h1>🌼 Ofrenda for the agents who didn't make it</h1>{cards}</main>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("traces", nargs="+")
    ap.add_argument("--model", default="gemma3:4b")
    ap.add_argument("--html")
    a = ap.parse_args()
    rows = []
    for p in a.traces:
        tr = json.load(open(p))
        cause = coroner(tr)
        try:
            testimony = summon(tr, cause, a.model)
        except OSError as e:
            sys.exit(f"Ollama isn't answering at {OLLAMA}: {e}. Run `ollama serve` and `ollama pull {a.model}`.")
        kept, struck = cross_examine(testimony, len(tr["steps"]))
        rows.append({"name": tr["name"], "task": tr["task"], "cause": cause, "kept": kept, "struck": struck})
        print(f"\n⚰️  {tr['name']} | {cause}\n" + "\n".join("  👻 " + s for s in kept)
              + ("".join(f"\n  ✂️  struck: {s}" for s in struck)))
    if a.html:
        open(a.html, "w").write(ofrenda(rows))
        print(f"\nofrenda written to {a.html}")


if __name__ == "__main__":
    main()
