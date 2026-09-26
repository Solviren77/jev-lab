"""Save each experiment-2 prompt variant as a Jev Lab scenario on one docket-49 file, so the
variants can be opened, edited and compared side by side in the page.

  python3 to_scenarios.py [FILE]   (default: triage.py)
"""
import json
import sys
from pathlib import Path

import scan
import variants

LABELS = {"more_than_name": "does more than its name says", "mixes_io_logic": "mixes I/O with logic",
          "repeated_work": "redoes the same work every call", "duplicate": "duplicates another function"}
TITLES = {"control": "original prompt", "statement": "statements not questions",
          "no_criteria": "no yes/no definitions", "examples": "examples in definitions",
          "literal": "literal wording", "facts": "code facts in context"}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "triage.py"
    path = variants.ROOT / name
    fns = scan.functions(path)
    home = Path.home() / ".jev-lab/scenarios"
    home.mkdir(parents=True, exist_ok=True)
    for i, (v, spec) in enumerate(variants.V.items(), 1):
        qs = {}
        for f in fns:
            ref = "`%s`" % f["name"]
            for k in variants.KEYS:
                qs["%s__%s" % (f["name"], k)] = dict(scan.noul(spec["q"][k].format(id=ref), spec["c"].get(k)),
                                                     label="%s: %s" % (f["name"], LABELS[k]))
            qs["%s__duplicate" % f["name"]] = dict(scan.noul(spec["dup"].format(id=ref)),
                                                   label="%s: %s" % (f["name"], LABELS["duplicate"]))
        qs["most_attention"] = {"type": "choice", "label": "Which function most needs restructuring?",
                                "instructions": "Which single function in this file would most benefit from being "
                                                "simplified or restructured?",
                                "criteria": dict({f["name"]: f["name"] for f in fns}, none="No function needs it")}
        state = {}
        if spec.get("facts"):
            state["measured"] = {f["name"]: variants.facts(f, fns) for f in fns}
        s = {"name": "code-%s-%d-%s" % (Path(name).stem, i, v), "title": TITLES[v],
             "documents": [str(path)], "variables": {}, "state": state, "questions": qs}
        (home / (s["name"] + ".json")).write_text(json.dumps(s, indent=2) + "\n")
        print(s["name"], len(qs), "questions")


if __name__ == "__main__":
    main()
