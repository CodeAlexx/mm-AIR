#!/usr/bin/env bash
# MM-Air's checks that need no GPU, model or display. Run before every push:
#   tools/check.sh          static contract, compile every hand-run test program, screen wording
#   tools/check.sh --tests  the above, then `airproj test` (builds and runs the declared tests)
# AIR is found at $AIR_ROOT or ../AIR; its built tools at $AIR_TOOLCHAIN or $AIR_ROOT/build-release.
set -euo pipefail
app=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
air=$(cd -- "${AIR_ROOT:-$app/../AIR}" && pwd)
tools=${AIR_TOOLCHAIN:-$air/build-release}
[[ -x $tools/bin/airc ]] || { echo "no airc in $tools/bin (set AIR_TOOLCHAIN)" >&2; exit 2; }
cd "$app"

AIR_ROOT=$air python3 -B test_contract.py

# Programs run by hand are declared under targets.check: compile each (no build).
failed=0
while read -r file; do
  if ! out=$("$tools/bin/airc" check "$file" 2>&1); then
    echo "$file: does not compile"; echo "$out" | tail -5; failed=1
  fi
done < <(python3 -c 'import json; [print(e["entry"]) for e in json.load(open("air.project.json"))["targets"].get("check", [])]')
[[ $failed == 0 ]] || exit 1
echo "hand-run test programs compile"

# Wording on screens: users are not developers. Only findings not in the baseline fail.
python3 "$air/tools/ui-text-check.py" "$app" --baseline tests/ui-text-baseline.txt

if [[ ${1:-} == --tests ]]; then
  "$tools/bin/airproj" --project "$app" --toolchain "$tools" test
fi
