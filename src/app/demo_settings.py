from __future__ import annotations

from app.settings import Settings
import json


def run_demo():
    s = Settings()
    print("Loaded settings from:", s.path)
    print("Current thread_cap:", s.get("General", "thread_cap"))

    # modify a value
    s.set("General", "thread_cap", 4)
    s.save()
    print("Set thread_cap to 4 and saved")

    # reload and show
    s2 = Settings()
    print("Reloaded thread_cap:", s2.get("General", "thread_cap"))

    # dump a small part
    print(json.dumps({"General": s2.as_dict().get("General")}, indent=2))


if __name__ == "__main__":
    run_demo()
