import os

for k in [k for k in os.environ if "proxy" in k.lower()]:
    os.environ.pop(k, None)

import httpx

d = httpx.Client(timeout=20, trust_env=False).get("http://127.0.0.1:8000/openapi.json").json()
for path, ops in d["paths"].items():
    for method, op in ops.items():
        params = ",".join(
            p["name"] + ("" if p.get("required") else "?") for p in op.get("parameters", [])
        )
        body = ""
        rb = op.get("requestBody")
        if rb:
            schema = list(rb["content"].values())[0]["schema"]
            body = " body=" + str(schema.get("$ref") or schema).split("/")[-1]
        print(f"{method.upper():6} {path:44} {params}{body}")
