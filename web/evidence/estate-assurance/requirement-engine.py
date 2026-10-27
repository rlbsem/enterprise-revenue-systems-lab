"""Least-information fixed point over typed dependency groups.

UNKNOWN is the initial value, not a failure. Positive rules refine it only when a
foundation is established. Optional inputs never drive mandatory group status.
"""

from .compatibility import compare

SUPPORTED, UNSUPPORTED, UNKNOWN = "SUPPORTED", "UNSUPPORTED", "UNKNOWN"


def combine(mode, states):
    if not states:
        return UNKNOWN  # an empty declaration is not a proof of support
    if mode == "ALL":
        return UNSUPPORTED if UNSUPPORTED in states else UNKNOWN if UNKNOWN in states else SUPPORTED
    if mode == "ANY":
        return SUPPORTED if SUPPORTED in states else UNKNOWN if UNKNOWN in states else UNSUPPORTED
    raise ValueError("invalid group mode")


def evaluate(facts):
    states = {}
    evidence = {}
    definitions = {}
    for key, fact in facts.items():
        kind, subject = fact["kind"], fact["subject"]
        if kind == "system":
            evidence[f"sys:{subject}"] = fact["evidence"]
            states[f"sys:{subject}"] = (
                UNKNOWN
                if fact["state"] != SUPPORTED
                else SUPPORTED
                if fact["value"]["lifecycle"] == "active"
                else UNSUPPORTED
            )
        if kind == "requirement":
            states[f"req:{subject}"] = UNKNOWN
            definitions[subject] = fact
    for fact in facts.values():
        if fact["kind"] == "integration":
            evidence[f"int:{fact['subject']}"] = fact["evidence"]
            value = fact["value"]
            states[f"int:{fact['subject']}"] = (
                UNKNOWN
                if value is None
                else combine(
                    "ALL",
                    [
                        fact["state"],
                        *(
                            states.get(f"sys:{value[k]}", UNKNOWN)
                            for k in ("source", "destination", "runtime")
                        ),
                    ],
                )
            )

    def edge(key):
        fact = facts.get(key)
        if fact is None or fact["kind"] != "dependency" or fact["state"] != SUPPORTED:
            return {
                "state": UNKNOWN,
                "provider": None,
                "optional": False,
                "reason": "dependency unresolved",
                "evidence": [] if fact is None else fact["evidence"],
            }
        value = fact["value"]
        result = {
            "state": states.get(value["provider"], UNKNOWN),
            "provider": value["provider"],
            "optional": value["optional"],
            "reason": "typed dependency",
            "evidence": fact["evidence"],
        }
        if not value["qualified"]:
            result.update(state=UNSUPPORTED, reason="not an explicitly qualified provider")
        if value.get("contract"):
            contract = value["contract"]
            offered = facts.get(f"interface:{value['provider'].split(':', 1)[1]}")
            check = compare(
                contract, offered["value"] if offered and offered["state"] == SUPPORTED else None
            )
            result["compatibility"] = check
            result["evidence"] = sorted(
                set(result["evidence"] + (offered["evidence"] if offered else []))
            )
            result["state"] = combine("ALL", [result["state"], check["state"]])
        return result

    # Each node can refine UNKNOWN once. Synchronous passes avoid order sensitivity.
    for _ in range(len(definitions) + 1):
        new = dict(states)
        for subject, fact in sorted(definitions.items()):
            if fact["state"] != SUPPORTED:
                continue
            value = fact["value"]
            inputs = [edge(key) for key in value["inputs"]]
            new[f"req:{subject}"] = combine(
                value["mode"], [x["state"] for x in inputs if not x["optional"]]
            )
        if new == states:
            break
        states = new
    else:
        raise RuntimeError("requirement fixed point did not converge")
    return {
        "states": states,
        "evidence": evidence,
        "requirements": {
            subject: {
                "state": states[f"req:{subject}"],
                "mode": f["value"]["mode"] if f["value"] else None,
                "label": f["value"]["label"] if f["value"] else subject,
                "evidence": f["evidence"],
                "inputs": {key: edge(key) for key in f["value"]["inputs"]} if f["value"] else {},
            }
            for subject, f in sorted(definitions.items())
        },
    }
