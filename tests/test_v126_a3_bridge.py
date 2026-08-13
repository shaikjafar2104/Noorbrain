from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "dashboard" / "js" / "noorbrain-mobile-shell-v126.js"

NODE_CHECK = """
const calls = [];

function makeElement() {
  return {
    id: "",
    innerHTML: "",
    dataset: {},
    style: {},
    classList: { add() {}, remove() {}, toggle() {} },
    appendChild() { return null; },
    addEventListener() {},
    querySelectorAll() { return []; },
    querySelector() { return null; },
    setAttribute() {},
    getAttribute() { return ""; },
    closest() { return null; },
    scrollIntoView() {},
    scrollTop: 0,
  };
}

const document = {
  readyState: "complete",
  body: makeElement(),
  addEventListener() {},
  createElement() { return makeElement(); },
  getElementById() { return null; },
  querySelectorAll() { return []; },
  querySelector() { return null; },
};

const history = { pushState() {} };
const windowObj = {
  document,
  history,
  scrollTo() {},
  addEventListener() {},
  dispatchEvent(event) {
    calls.push({ type: event.type, detail: event.detail || {} });
    return true;
  },
  NoorMobileProductRouterV12: {
    open(module) {
      calls.push({ router: "open", module });
      return true;
    },
  },
  NoorBrainUnifiedUI: null,
};

global.window = windowObj;
global.document = document;
global.history = history;
global.console = console;
global.CustomEvent = class CustomEvent {
  constructor(type, init = {}) {
    this.type = type;
    this.detail = init.detail || {};
  }
};
global.setTimeout = () => 0;
global.clearTimeout = () => {};
global.URLSearchParams = class URLSearchParams {
  constructor() {}
  get() { return null; }
};
global.location = { hash: "", search: "" };

eval(require("fs").readFileSync(process.argv[1], "utf8"));

for (const action of ["devices", "camera", "activity"]) {
  const result = window.NoorBrainMobile126.action(action);
  console.log(JSON.stringify({ action, result, calls }));
  if (result !== true) process.exit(1);
  if (!calls.some((entry) => entry.router === "open" && entry.module === action)) {
    process.exit(2);
  }
}
process.exit(0);
"""


def main() -> int:
    if not JS_PATH.exists():
        raise FileNotFoundError(f"Missing JS shell file: {JS_PATH}")

    completed = subprocess.run(
        ["node", "-e", NODE_CHECK, str(JS_PATH)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip(), file=sys.stderr)

    if completed.returncode != 0:
        sys.exit(completed.returncode)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
