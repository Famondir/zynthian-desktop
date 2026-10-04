"""Load every enabled+available LV2 engine with jalv (as zynthian's engine
does: `jalv -s -n <name> <url>`) against a private dummy JACK server, so a
running Zynthian session isn't touched. OK = jalv reaches its '>' prompt."""
import json, os, select, subprocess, sys, time

D = os.path.dirname(os.path.abspath(__file__))
plugins = json.load(open(f"{D}/audit_list.json"))
env = {**os.environ, "JACK_DEFAULT_SERVER": "audit", "LD_LIBRARY_PATH": "/usr/lib/x86_64-linux-gnu"}
env.pop("DISPLAY", None)
jackd = subprocess.Popen(["jackd", "-n", "audit", "-d", "dummy", "-r", "48000", "-p", "512"], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
results = []
try:
    for i, (key, url, typ) in enumerate(plugins):
        t0 = time.time()
        p = subprocess.Popen(["jalv", "-s", "-n", f"audit{i}", url], env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = b""
        status = "TIMEOUT"
        while time.time() - t0 < 20:
            r, _, _ = select.select([p.stdout], [], [], 0.5)
            if r:
                chunk = os.read(p.stdout.fileno(), 65536)
                if not chunk:
                    status = f"EXIT {p.wait()}"
                    break
                out += chunk
                if b"\n> " in out or out.startswith(b"> ") or out.rstrip().endswith(b">"):
                    status = "OK"
                    break
            elif p.poll() is not None:
                status = f"EXIT {p.returncode}"
                break
        p.kill(); p.wait()
        text = out.decode(errors="replace")
        errs = [l for l in text.splitlines() if "error" in l.lower() or "fail" in l.lower() or "abort" in l.lower()]
        results.append({"key": key, "type": typ, "status": status, "secs": round(time.time() - t0, 1),
                        "errors": errs[:3], "tail": text[-300:] if status != "OK" else ""})
        print(f"{status:8s} {key}", flush=True)
finally:
    jackd.kill()
json.dump(results, open(f"{D}/audit_results.json", "w"), indent=1)
bad = [r for r in results if r["status"] != "OK"]
print(f"\n{len(results) - len(bad)} OK, {len(bad)} not OK")
