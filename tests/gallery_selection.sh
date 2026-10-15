#!/usr/bin/env bash
# Real pointer regression against the native application on an isolated X11/DBus
# desktop. No generation/GPU inference unless explicitly opted in below.
# Usage: bash gallery_selection.sh APP AIR_UI XVFB LAYOUT CSS VIDEO_A VIDEO_B
# Set MM_AIR_TEST_SCALE=2 to exercise HiDPI on the private 4K display.
# Pointer input uses xdotool/XTest; accessibility supplies control discovery.
# MM_AIR_TEST_LAYOUT=1 also verifies configured Edit panel/navigation dimensions.
# Set MM_AIR_TEST_PARAMETERS=FILE.json to test reference reordering instead of
# history hover. The fixture must contain at least two visual and two audio refs.
# Set MM_AIR_TEST_IMAGE_REFERENCE=1 with PNG inputs to exercise the selected
# image -> H3 reference action through the real application without generation.
# MM_AIR_TEST_KREA_PARAMETERS=FILE.json restores Krea controls and verifies
# Generate fails at the intentionally absent asset setting, before GPU work.
# Add MM_AIR_TEST_GENERATE=1 to retain the real Krea asset environment and run
# actual Generate (720 seconds maximum), requiring visible progress and history.
# MM_AIR_TEST_H3_GENERATE_PARAMETERS=FILE.json selects the same opt-in real H3
# test. Both real modes require MM_AIR_TEST_GENERATE=1; filenames are automatic.
# MM_AIR_TEST_QWEN_EDIT_PARAMETERS=FILE.json runs the real Qwen Edit control.
# MM_AIR_TEST_LORAS=1 verifies restored LoRA controls and persistence first;
# MM_AIR_TEST_LORAS_ONLY=1 stops after that UI-only gate.
# MM_AIR_TEST_AUTOMATIC_OUTPUT=1 presses H3 Generate twice with unselected
# policies; fresh paths are chosen with no dialog and no worker may start.
set -Eeuo pipefail
trap 'echo "gallery regression failed at line $LINENO" >&2' ERR

if [[ ${1:-} != --inside ]]; then
  [[ $# == 7 ]] || { echo "usage: $0 APP AIR_UI XVFB LAYOUT CSS VIDEO_A VIDEO_B" >&2; exit 2; }
  scratch=$(mktemp -d /tmp/mm-air-gallery.XXXXXXXX)
  xvfb_pid=
  cleanup() {
    if [[ -n $xvfb_pid ]]; then kill "$xvfb_pid" 2>/dev/null || true; wait "$xvfb_pid" 2>/dev/null || true; fi
    rm -rf -- "$scratch"
  }
  trap cleanup EXIT
  mkdir -p "$scratch/data/mm-air" "$scratch/cache" "$scratch/config"
  printf 'XDG_DOWNLOAD_DIR="%s/downloads"\n' "$scratch" > "$scratch/config/user-dirs.dirs"
  jq -n --arg first "$6" --arg second "$7" \
    '{schema:"mm-air.generate.history",version:1,items:[
      {path:$first,thumbnail:"",parameters:"{}"},
      {path:$second,thumbnail:"",parameters:"{}"}]}' \
    > "$scratch/data/mm-air/generate-history.json"
  "$3" -displayfd 3 -screen 0 3840x2160x24 -nolisten tcp \
    3> "$scratch/display" > "$scratch/xvfb.log" 2>&1 &
  xvfb_pid=$!
  for ((i=0;i<100;i++)); do [[ -s $scratch/display ]] && break; sleep 0.05; done
  [[ -s $scratch/display ]] || { cat "$scratch/xvfb.log" >&2; exit 1; }
  display_number=$(<"$scratch/display")
  env DISPLAY=":$display_number" GDK_BACKEND=x11 \
    GDK_SCALE="${MM_AIR_TEST_SCALE:-1}" GSK_RENDERER=cairo LIBGL_ALWAYS_SOFTWARE=1 GDK_DEBUG=no-portals \
    GTK_A11Y=atspi GIO_USE_VFS=local \
    XDG_DATA_HOME="$scratch/data" XDG_CACHE_HOME="$scratch/cache" XDG_CONFIG_HOME="$scratch/config" \
    bash "$0" --inside "$scratch" "$1" "$2" "$4" "$5" "$6" "$7"
  exit
fi

scratch=$2
app=$3
helper=$4
layout=$5
css=$6
first_name=$(basename "$7")
first_path=$7
second_path=$8
app_pid=
bus_pid=
registry_pid=
generation_watchdog=
cleanup_inside() {
  if [[ -n $generation_watchdog ]]; then
    kill "$generation_watchdog" 2>/dev/null || true
    wait "$generation_watchdog" 2>/dev/null || true
  fi
  for child in "$app_pid" "$registry_pid" "$bus_pid"; do
    if [[ -n $child ]]; then
      kill "$child" 2>/dev/null || true
      wait "$child" 2>/dev/null || true
    fi
  done
}
trap cleanup_inside EXIT
diagnose_failure() {
  echo "gallery regression failed at line $1" >&2
  if [[ -n ${cache:-} ]]; then
    jq -r '.data[0][] | .[6] | select(length > 0)' <<< "$cache" >&2 || true
  fi
  [[ ! -f $scratch/app.out ]] || { echo "MM-Air stdout:" >&2; cat "$scratch/app.out" >&2; }
  [[ ! -f $scratch/app.err ]] || { echo "MM-Air stderr:" >&2; cat "$scratch/app.err" >&2; }
}
trap 'diagnose_failure "$LINENO"' ERR
# GTK may wait for portals on a private session bus. Keep the ordinary session
# bus for settings, but own the accessibility bus/registry on this Xvfb display.
# Starting the registry before GTK also avoids an empty accessible root.
export AT_SPI_BUS_ADDRESS="unix:path=$scratch/a11y-bus"
dbus-daemon --config-file=/usr/share/defaults/at-spi2/accessibility.conf \
  --address="$AT_SPI_BUS_ADDRESS" --nofork > "$scratch/a11y.log" 2>&1 &
bus_pid=$!
for ((i=0;i<100;i++)); do [[ -S $scratch/a11y-bus ]] && break; sleep 0.05; done
[[ -S $scratch/a11y-bus ]] || { cat "$scratch/a11y.log" >&2; exit 1; }
a11y=$AT_SPI_BUS_ADDRESS
/usr/libexec/at-spi2-registryd > "$scratch/registry.log" 2>&1 &
registry_pid=$!
registry_ready=false
for ((i=0;i<100;i++)); do
  if busctl --address="$a11y" --json=short call org.a11y.atspi.Registry \
      /org/a11y/atspi/accessible/root org.a11y.atspi.Accessible GetChildren \
      >/dev/null 2>&1; then registry_ready=true; break; fi
  sleep 0.05
done
[[ $registry_ready == true ]] || { cat "$scratch/registry.log" >&2; exit 1; }
if [[ -n ${MM_AIR_TEST_KREA_PARAMETERS:-} ]]; then
  if [[ ${MM_AIR_TEST_GENERATE:-0} == 1 ]]; then
    "$app" --parameters "$MM_AIR_TEST_KREA_PARAMETERS" > "$scratch/app.out" 2> "$scratch/app.err" &
  else
    env -u MM_AIR_KREA_MODEL "$app" --parameters "$MM_AIR_TEST_KREA_PARAMETERS" > "$scratch/app.out" 2> "$scratch/app.err" &
  fi
elif [[ -n ${MM_AIR_TEST_H3_GENERATE_PARAMETERS:-} ]]; then
  [[ ${MM_AIR_TEST_GENERATE:-0} == 1 ]] || {
    echo "H3 generation requires explicit MM_AIR_TEST_GENERATE=1" >&2; exit 2;
  }
  "$app" --parameters "$MM_AIR_TEST_H3_GENERATE_PARAMETERS" > "$scratch/app.out" 2> "$scratch/app.err" &
elif [[ -n ${MM_AIR_TEST_QWEN_EDIT_PARAMETERS:-} ]]; then
  [[ ${MM_AIR_TEST_GENERATE:-0} == 1 ]] || {
    echo "Qwen editing requires explicit MM_AIR_TEST_GENERATE=1" >&2; exit 2;
  }
  "$app" --parameters "$MM_AIR_TEST_QWEN_EDIT_PARAMETERS" > "$scratch/app.out" 2> "$scratch/app.err" &
elif [[ -n ${MM_AIR_TEST_PARAMETERS:-} ]]; then
  "$app" --parameters "$MM_AIR_TEST_PARAMETERS" > "$scratch/app.out" 2> "$scratch/app.err" &
else
  "$app" "$layout" "$css" "$helper" > "$scratch/app.out" 2> "$scratch/app.err" &
fi
app_pid=$!
peer=
app_ready=false
for ((i=0;i<500;i++)); do
  peer=$(busctl --address="$a11y" list --no-pager --no-legend | awk '$3 == "air-ui" {print $1; exit}')
  if [[ -n $peer ]] && busctl --address="$a11y" --json=short call "$peer" \
      /org/a11y/atspi/accessible/root org.a11y.atspi.Accessible GetChildren \
      2>/dev/null | jq -e '.data[0] | length > 0' >/dev/null; then app_ready=true; break; fi
  sleep 0.1
done
[[ $app_ready == true ]] || { echo "no ready accessible air-ui process" >&2; cat "$scratch/app.err" >&2; busctl --address="$a11y" list --no-pager >&2; exit 1; }
call() { busctl --address="$a11y" --json=short call "$peer" "$@"; }
mouse() {
  # AT-SPI can return success without moving the pointer on a private bus
  # (observed with GTK 4.22). Send real X11 input and verify its destination.
  xdotool mousemove --sync "$1" "$2"
  local pointer
  pointer=$(xdotool getmouselocation --shell)
  [[ $(sed -n 's/^X=//p' <<< "$pointer") == "$1" &&
     $(sed -n 's/^Y=//p' <<< "$pointer") == "$2" ]]
  case "$3" in
    abs) ;;
    b1c) xdotool click 1 ;;
    *) echo "unsupported test mouse event: $3" >&2; return 2 ;;
  esac
}
# GTK exports descendants lazily. Walk only this test application's tree.
queue=(/org/a11y/atspi/accessible/root)
for ((i=0;i<${#queue[@]};i++)); do
  [[ $i -lt 512 ]] || { echo "unexpected accessible tree size" >&2; exit 1; }
  mapfile -t children < <(call "${queue[i]}" org.a11y.atspi.Accessible GetChildren |
    jq -r '.data[0][] | .[1]')
  queue+=("${children[@]}")
done
cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
if [[ ${MM_AIR_TEST_AUTOMATIC_OUTPUT:-0} == 1 ]]; then
  [[ ${MM_AIR_TEST_GENERATE:-0} != 1 && -z ${MM_AIR_TEST_KREA_PARAMETERS:-} &&
     -z ${MM_AIR_TEST_PARAMETERS:-} && -z ${MM_AIR_TEST_H3_GENERATE_PARAMETERS:-} ]]
  generate=$(jq -r '.data[0][] | select(.[6] == "Generate H3 MP4" and .[7] == 43) | .[0][1]' <<< "$cache")
  [[ -n $generate ]]
  for click in 1 2; do
    call "$generate" org.a11y.atspi.Action DoAction i 0 >/dev/null
    for ((attempt=0;attempt<30;attempt++)); do
      [[ $(rg -c '^mm-air automatic H3 output=' "$scratch/app.out" || true) -ge $click ]] && break
      sleep 0.1
    done
  done
  mapfile -t outputs < <(sed -n 's/^mm-air automatic H3 output=//p' "$scratch/app.out")
  [[ ${#outputs[@]} == 2 && ${outputs[0]} != "${outputs[1]}" ]]
  for output in "${outputs[@]}"; do
    [[ $output == "$(dirname "$(dirname "$(dirname "$app")")")/output/h3/"*.mp4 ]]
    [[ -d $(dirname "$output") && ! -e $output ]]
  done
  roots=$(call /org/a11y/atspi/accessible/root org.a11y.atspi.Accessible GetChildren)
  [[ $(jq '.data[0] | length' <<< "$roots") == 1 ]]
  ! rg -q 'Choose an output file|^mm-air started linked AIR|^mm-air generated media saved=' "$scratch/app.out"
  jq -e '.items | length == 2' "$scratch/data/mm-air/generate-history.json" >/dev/null
  echo "PASS: H3 Generate chooses fresh output/h3 MP4 paths without a dialog; explicit-policy validation starts no worker"
  exit 0
fi
run_generation() {
  local fixture=$1 model=$2 action_name=$3 output action last_labels= elapsed_first=
  local elapsed_advanced=false sampled=false decoded=false saved=false labels elapsed stage
  output=
  action=$(jq -r --arg name "$action_name" '.data[0][] |
    select(.[6] == $name and .[7] == 43) | .[0][1]' <<< "$cache")
  [[ -n $action ]] || { echo "Missing real Generate action: $action_name" >&2; return 1; }
  local seed_lock= candidate state extent window_info origin_x origin_y x y
  while read -r candidate; do
    state=$(call "$candidate" org.a11y.atspi.Accessible GetState)
    if jq -e '((.data[0][0] / 33554432 | floor) % 2) == 1' <<< "$state" >/dev/null; then
      seed_lock=$candidate
      break
    fi
  done < <(jq -r '.data[0][] | select(.[6] == "Lock" and .[7] == 7) | .[0][1]' <<< "$cache")
  [[ -n $seed_lock ]] || { echo "Missing seed Lock checkbox" >&2; return 1; }
  if ! call "$seed_lock" org.a11y.atspi.Accessible GetState | jq -e '((.data[0][0] / 16 | floor) % 2) == 1' >/dev/null; then
    # GtkCheckButton exposes state and bounds but no Action on current GTK.
    # Click the visible native checkbox, as the LoRA toggle test does below.
    extent=$(call "$seed_lock" org.a11y.atspi.Component GetExtents u 1)
    window_info=$(xwininfo -name 'MM-AIR · MiniMax H3 Studio')
    origin_x=$(awk '/Absolute upper-left X:/ {print $4}' <<< "$window_info")
    origin_y=$(awk '/Absolute upper-left Y:/ {print $4}' <<< "$window_info")
    x=$(jq --argjson origin "$origin_x" --argjson scale "$GDK_SCALE" '.data[0] | $origin + $scale * (.[0]+12)' <<< "$extent")
    y=$(jq --argjson origin "$origin_y" --argjson scale "$GDK_SCALE" '.data[0] | $origin + $scale * (.[1]+(.[3]/2|floor))' <<< "$extent")
    xdotool mousemove --sync "$x" "$y" click 1
    sleep 0.2
  fi
  state=$(call "$seed_lock" org.a11y.atspi.Accessible GetState)
  jq -e '((.data[0][0] / 16 | floor) % 2) == 1' <<< "$state" >/dev/null || {
    echo "Seed Lock did not toggle: path=$seed_lock bounds=${extent:-} point=${x:-},${y:-} state=$state" >&2
    return 1
  }
  # Bound the owned native process even if accessibility stops responding. This
  # watchdog never targets the user's desktop or an unrelated generation.
  ( timer=
    trap '[[ -z $timer ]] || kill "$timer" 2>/dev/null || true; exit 0' TERM INT
    sleep 720 & timer=$!; wait "$timer"
    kill "$app_pid" 2>/dev/null || true
    sleep 5 & timer=$!; wait "$timer"
    kill -KILL "$app_pid" 2>/dev/null || true ) &
  generation_watchdog=$!
  local started=$SECONDS
  call "$action" org.a11y.atspi.Action DoAction i 0 >/dev/null
  while ((SECONDS - started < 720)); do
    if [[ -z $output ]]; then
      if [[ $model == Qwen ]]; then
        output=$(sed -n 's/^mm-air generated media saved=//p' "$scratch/app.out" | tail -1)
      else
        output=$(sed -n "s/^mm-air automatic $model output=//p" "$scratch/app.out" | tail -1)
      fi
      if [[ -n $output ]]; then
        folder=h3; extension=mp4
        if [[ $model == Krea ]]; then folder=krea; extension=png; fi
        if [[ $model == Qwen ]]; then folder=qwen-image-2.1/edit; extension=png; fi
        local expected_root=${MM_AIR_OUTPUT_ROOT:-$(dirname "$(dirname "$(dirname "$app")")")/output}
        [[ $output == "$expected_root/$folder/"*.$extension ]]
      fi
    fi
    kill -0 "$app_pid" 2>/dev/null || { echo "Native app exited during generation" >&2; return 1; }
    # A completed render may briefly stall the accessibility cache while GTK
    # realizes the new history tile. Admit the authoritative file, history,
    # and app-stage evidence before making another bounded bus query.
    if [[ -n $output && -s $output ]] && jq -e --arg output "$output" \
        '.items[] | select(.path == $output)' "$scratch/data/mm-air/generate-history.json" >/dev/null; then
      [[ $sampled == true && $decoded == true && $elapsed_advanced == true ]] || {
        echo "Missing visible sampling/decode/advancing elapsed evidence: sampled=$sampled decoded=$decoded elapsed=$elapsed_advanced" >&2; return 1;
      }
      if [[ $model == Qwen ]]; then
        [[ $saved == true ]] || rg -q '^mm-air status: VAE decoded · encoding and saving PNG' "$scratch/app.out"
      else
        [[ $saved == true ]] || rg -q "^mm-air status: $model encoding and saving" "$scratch/app.out"
      fi
      rg -Fq "mm-air generated media saved=$output" "$scratch/app.out"
      jq -e --slurpfile requested "$fixture" '.seed == $requested[0].seed and .width == $requested[0].width and .height == $requested[0].height' "$output.json" >/dev/null
      if [[ $model == Qwen ]]; then
        jq -e --slurpfile requested "$fixture" '.mode == "edit" and .source == $requested[0].source and .references == $requested[0].references and .steps == $requested[0].steps' "$output.json" >/dev/null
      fi
      echo "PASS: real native $model Generate, visible sampling/decode/elapsed, saved file and history: $output"
      stat -c 'artifact=%n bytes=%s' "$output"
      if [[ -n ${MM_AIR_TEST_ARTIFACT_DIRECTORY:-} ]]; then
        mkdir -p "$MM_AIR_TEST_ARTIFACT_DIRECTORY"
        cp -- "$output" "$output.json" "$scratch/app.out" "$scratch/app.err" "$MM_AIR_TEST_ARTIFACT_DIRECTORY/"
      fi
      return 0
    fi
    cache=$(timeout 5s busctl --address="$a11y" --json=short call "$peer" \
      /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
    labels=$(jq -r '.data[0][] | .[6] | select(length > 0)' <<< "$cache" | sort -u)
    if [[ $labels != "$last_labels" ]]; then
      while IFS= read -r stage; do
        [[ $stage =~ ^(H3\ |Krea\ |Sampling\ |Prompt\ |VAE\ |Loading\ |Elapsed:|Generating|MiniMax-H3\ MP4\ saved|Linked\ AIR\ Krea) ]] || continue
        echo "UI +$((SECONDS - started))s: $stage"
      done <<< "$labels"
      last_labels=$labels
    fi
    elapsed=$(sed -n -e 's/^Elapsed: \([0-9][0-9]*\) s$/\1/p' \
      -e 's/^Generating · \([0-9][0-9]*\) s$/\1/p' <<< "$labels" | head -1)
    if [[ -n $elapsed ]]; then
      if [[ -z $elapsed_first ]]; then elapsed_first=$elapsed
      elif ((elapsed > elapsed_first)); then elapsed_advanced=true; fi
    fi
    [[ ! $labels =~ $model\ sampling\ step\ [0-9]+/ ]] || sampled=true
    [[ ! $labels =~ $model\ decoding ]] || decoded=true
    [[ ! $labels =~ $model\ encoding\ and\ saving ]] || saved=true
    if [[ $model == Qwen ]]; then
      [[ ! $labels =~ Sampling.*step\ [0-9]+/ ]] || sampled=true
      [[ ! $labels =~ Sampling\ complete.*decoding\ VAE ]] || decoded=true
      [[ ! $labels =~ VAE\ decoded.*encoding\ and\ saving ]] || saved=true
    fi
    if rg -q '^mm-air generation failed:' "$scratch/app.err" ||
       jq -e '.data[0][] | select(.[6] == "Failed")' <<< "$cache" >/dev/null; then
      echo "Native generation reported failure" >&2; return 1
    fi
    if [[ $model != Qwen ]] && ((SECONDS - started >= 15)) && ! rg -q '^mm-air started linked AIR' "$scratch/app.out"; then
      echo "Generate never submitted a native worker (validation or UI failure)" >&2; return 1
    fi
    sleep 0.5
  done
  echo "Native $model UI generation exceeded 720 seconds; stopping owned app" >&2
  kill "$app_pid" 2>/dev/null || true
  return 1
}
if [[ -n ${MM_AIR_TEST_QWEN_EDIT_PARAMETERS:-} ]]; then
  for ((attempt=0;attempt<30;attempt++)); do
    cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
    if jq -e '.data[0][] | select(.[6] == "Qwen Image Edit parameters restored")' <<< "$cache" >/dev/null; then break; fi
    sleep 0.1
  done
  jq -e '.data[0][] | select(.[6] == "Qwen Image Edit parameters restored")' <<< "$cache" >/dev/null
  run_generation "$MM_AIR_TEST_QWEN_EDIT_PARAMETERS" Qwen "Generate Edit"
  exit 0
fi
if [[ -n ${MM_AIR_TEST_H3_GENERATE_PARAMETERS:-} ]]; then
  for ((attempt=0;attempt<30;attempt++)); do
    cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
    if jq -e '.data[0][] | select(.[6] == "Generate parameters restored")' <<< "$cache" >/dev/null; then break; fi
    sleep 0.1
  done
  jq -e '.data[0][] | select(.[6] == "Generate parameters restored")' <<< "$cache" >/dev/null
  if [[ ${MM_AIR_TEST_LORAS:-0} == 1 ]]; then
    queue=(/org/a11y/atspi/accessible/root)
    for ((j=0;j<${#queue[@]};j++)); do
      [[ $j -lt 1024 ]] || exit 1
      mapfile -t children < <(call "${queue[j]}" org.a11y.atspi.Accessible GetChildren |
        jq -r '.data[0][] | .[1]')
      queue+=("${children[@]}")
    done
    cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
    h3_lora=$(jq -r '.loras[0].path | split("/")[-1]' "$MM_AIR_TEST_H3_GENERATE_PARAMETERS")
    jq -e --arg lora "$h3_lora" '.data[0][] | select(.[6] == $lora)' <<< "$cache" >/dev/null
    jq -e '.data[0][] | select(.[6] == "Model LoRA")' <<< "$cache" >/dev/null
    save=$(jq -r '.data[0][] | select(.[6] == "Save parameters" and .[7] == 43) | .[0][1]' <<< "$cache")
    call "$save" org.a11y.atspi.Action DoAction i 0 >/dev/null
    saved=
    for ((attempt=0;attempt<30;attempt++)); do
      saved=$(sed -n 's/^mm-air parameters saved=//p' "$scratch/app.out" | tail -1)
      [[ -n $saved && -s $saved ]] && break
      sleep 0.1
    done
    [[ -n $saved && -s $saved ]]
    jq -e --arg path "$(jq -r '.loras[0].path' "$MM_AIR_TEST_H3_GENERATE_PARAMETERS")" \
      '.transformer_projection == 3 and (.loras|length) == 1 and
       .loras[0].path == $path and .loras[0].enabled == true' "$saved" >/dev/null
    echo "PASS: native H3 LoRA control restored visibly and persisted in Generate parameters"
    if [[ ${MM_AIR_TEST_LORAS_ONLY:-0} == 1 ]]; then exit 0; fi
  fi
  run_generation "$MM_AIR_TEST_H3_GENERATE_PARAMETERS" H3 "Generate H3 MP4"
  exit 0
fi
if [[ -n ${MM_AIR_TEST_KREA_PARAMETERS:-} ]]; then
  for ((attempt=0;attempt<30;attempt++)); do
    cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
    if jq -e '.data[0][] | select(.[6] == "Krea Generate parameters restored")' <<< "$cache" >/dev/null; then break; fi
    sleep 0.1
  done
  jq -e '.data[0][] | select(.[6] == "Krea Generate parameters restored")' <<< "$cache" >/dev/null
  expected_krea=$(jq -r '"\(.width) × \(.height)"' "$MM_AIR_TEST_KREA_PARAMETERS")
  jq -e --arg expected "$expected_krea" '.data[0][] | select(.[6] == $expected)' <<< "$cache" >/dev/null
  if [[ ${MM_AIR_TEST_LORAS:-0} == 1 ]]; then
    refresh_lora_tree() {
      queue=(/org/a11y/atspi/accessible/root)
      for ((j=0;j<${#queue[@]};j++)); do
        [[ $j -lt 1024 ]] || return 1
        mapfile -t children < <(call "${queue[j]}" org.a11y.atspi.Accessible GetChildren | jq -r '.data[0][] | .[1]')
        queue+=("${children[@]}")
      done
      cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
    }
    snapshot_loras() {
      local previous=${saved:-}
      refresh_lora_tree
      save=$(jq -r '.data[0][] | select(.[6] == "Save parameters" and .[7] == 43) | .[0][1]' <<< "$cache")
      call "$save" org.a11y.atspi.Action DoAction i 0 >/dev/null
      for ((attempt=0;attempt<30;attempt++)); do
        saved=$(sed -n 's/^mm-air parameters saved=//p' "$scratch/app.out" | tail -1)
        [[ -n $saved && $saved != "$previous" && -s $saved ]] && return
        sleep 0.1
      done
      return 1
    }
    refresh_lora_tree
    first_lora=$(jq -r '.loras[0].path | split("/")[-1]' "$MM_AIR_TEST_KREA_PARAMETERS")
    grid=$(jq -r --arg name "$first_lora" '.data[0] as $items |
      [$items[] | select(.[6] == $name) | .[2][1]] as $parents |
      $items[] | select(.[0][1] as $path | $parents | index($path)) |
      select(.[5] | index("org.a11y.atspi.Selection")) | .[0][1]' <<< "$cache" | head -1)
    [[ -n $grid ]]
    call "$grid" org.a11y.atspi.Selection SelectChild i 0 >/dev/null
    sleep 0.2
    refresh_lora_tree
    enabled=$(jq -r '.data[0][] | select(.[6] == "Enabled" and .[7] == 7) | .[0][1]' <<< "$cache")
    strength=
    while IFS= read -r widget; do
      current=$(busctl --address="$a11y" --json=short get-property "$peer" "$widget" org.a11y.atspi.Value CurrentValue | jq -r '.data')
      if jq -e '. == 0.75' <<< "$current" >/dev/null; then strength=$widget; break; fi
    done < <(jq -r '.data[0][] | select(.[5] | index("org.a11y.atspi.Value")) | .[0][1]' <<< "$cache")
    [[ -n $strength ]]
    busctl --address="$a11y" set-property "$peer" "$strength" org.a11y.atspi.Value CurrentValue d 1.25
    sleep 0.2
    extent=$(call "$enabled" org.a11y.atspi.Component GetExtents u 1)
    window_info=$(xwininfo -name 'MM-AIR · MiniMax H3 Studio')
    origin_x=$(awk '/Absolute upper-left X:/ {print $4}' <<< "$window_info")
    origin_y=$(awk '/Absolute upper-left Y:/ {print $4}' <<< "$window_info")
    x=$(jq --argjson origin "$origin_x" --argjson scale "$GDK_SCALE" '.data[0] | $origin + $scale * (.[0]+12)' <<< "$extent")
    y=$(jq --argjson origin "$origin_y" --argjson scale "$GDK_SCALE" '.data[0] | $origin + $scale * (.[1]+(.[3]/2|floor))' <<< "$extent")
    mouse "$x" "$y" abs
    mouse "$x" "$y" b1c
    sleep 0.2
    snapshot_loras
    jq -e '.loras[0].enabled == false and .loras[0].strength == 1.25 and (.loras|length)==2' "$saved" >/dev/null
    remove=$(jq -r '.data[0][] | select(.[6] == "Remove LoRA" and .[7] == 43) | .[0][1]' <<< "$cache")
    call "$remove" org.a11y.atspi.Action DoAction i 0 >/dev/null
    sleep 0.2
    snapshot_loras
    jq -e '(.loras|length)==1' "$saved" >/dev/null
    clear=$(jq -r '.data[0][] | select(.[6] == "Clear LoRAs" and .[7] == 43) | .[0][1]' <<< "$cache")
    call "$clear" org.a11y.atspi.Action DoAction i 0 >/dev/null
    sleep 0.2
    snapshot_loras
    jq -e '.loras == []' "$saved" >/dev/null
    echo "PASS: native LoRA restore, selection, strength edit, toggle, individual removal, clear all, and parameter persistence"
    exit 0
  fi
  if [[ ${MM_AIR_TEST_GENERATE:-0} == 1 ]]; then
    run_generation "$MM_AIR_TEST_KREA_PARAMETERS" Krea "Generate Krea PNG"
    exit 0
  fi
  generate=$(jq -r '.data[0][] | select(.[6] == "Generate Krea PNG" and .[7] == 43) | .[0][1]' <<< "$cache")
  [[ -n $generate ]] || { echo "native Krea Generate action missing" >&2; exit 1; }
  call "$generate" org.a11y.atspi.Action DoAction i 0 >/dev/null
  for ((attempt=0;attempt<30;attempt++)); do
    cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
    if jq -e '.data[0][] | select(.[6] == "Set MM_AIR_KREA_MODEL")' <<< "$cache" >/dev/null; then break; fi
    sleep 0.1
  done
  jq -e '[.data[0][] | select(.[6] == "Set MM_AIR_KREA_MODEL")] | length >= 2' <<< "$cache" >/dev/null
  automatic_output=$(sed -n 's/^mm-air automatic Krea output=//p' "$scratch/app.out" | tail -1)
  [[ $automatic_output == "$(dirname "$(dirname "$(dirname "$app")")")/output/krea/"*.png ]]
  [[ -d $(dirname "$automatic_output") && ! -e $automatic_output ]]
  ! rg -q '^mm-air status: Choose an output file' "$scratch/app.out"
  roots=$(call /org/a11y/atspi/accessible/root org.a11y.atspi.Accessible GetChildren)
  [[ $(jq '.data[0] | length' <<< "$roots") == 1 ]]
  call "$generate" org.a11y.atspi.Action DoAction i 0 >/dev/null
  for ((attempt=0;attempt<30;attempt++)); do
    [[ $(rg -c '^mm-air automatic Krea output=' "$scratch/app.out") -ge 2 ]] && break
    sleep 0.1
  done
  next_output=$(sed -n 's/^mm-air automatic Krea output=//p' "$scratch/app.out" | tail -1)
  [[ $next_output != "$automatic_output" ]]
  echo "PASS: Krea Generate chooses fresh output/krea PNG paths without a dialog, reaches asset validation, and starts no GPU"
  exit 0
fi
if [[ -n ${MM_AIR_TEST_PARAMETERS:-} ]]; then
  # These actions go through the real GTK controls and AIR event loop. No GPU
  # request is submitted. The regular app Save/Generate reads these same lists.
  name_of() { busctl --address="$a11y" --json=short get-property "$peer" \
    "$1" org.a11y.atspi.Accessible Name | jq -r '.data'; }
  refresh_tree() {
    queue=(/org/a11y/atspi/accessible/root)
    for ((j=0;j<${#queue[@]};j++)); do
      [[ $j -lt 512 ]] || return 1
      mapfile -t children < <(call "${queue[j]}" org.a11y.atspi.Accessible GetChildren |
        jq -r '.data[0][] | .[1]')
      queue+=("${children[@]}")
    done
    cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
  }
  for ((attempt=0;attempt<30;attempt++)); do
    refresh_tree
    if jq -e '.data[0][] | select(.[6] == "Generate parameters restored")' <<< "$cache" >/dev/null; then break; fi
    sleep 0.1
  done
  jq -e '.data[0][] | select(.[6] == "Generate parameters restored")' <<< "$cache" >/dev/null
  for media in visual audio; do
    if [[ $media == visual ]]; then field=references; add_name='Add image / video'; else field=audio_references; add_name='Add audio'; fi
    mapfile -t expected < <(jq -r --arg field "$field" '.[$field][] | split("/")[-1]' "$MM_AIR_TEST_PARAMETERS")
    [[ ${#expected[@]} -ge 2 ]] || { echo "reference fixture needs two $media items" >&2; exit 2; }
    grid=$(jq -r --arg name "${expected[0]}" '
      .data[0] as $items | [$items[] | select(.[6] == $name) | .[2][1]] as $parents |
      $items[] | select(.[0][1] as $path | $parents | index($path)) |
      select(.[5] | index("org.a11y.atspi.Selection")) | .[0][1]' <<< "$cache" | head -1)
    # GTK labels also export Action, and Cache.GetItems has no stable order.
    # Select ATSPI_ROLE_PUSH_BUTTON (43), not its same-named text child (29).
    actions=$(jq -r --arg name "$add_name" '.data[0][] | select(.[6] == $name and .[7] == 43) |
      .[2][1]' <<< "$cache" | head -1)
    [[ -n $grid && -n $actions ]] || { echo "missing $media reference controls" >&2; exit 1; }
    mapfile -t buttons < <(call "$actions" org.a11y.atspi.Accessible GetChildren | jq -r '.data[0][] | .[1]')
    [[ ${#buttons[@]} == 4 ]] || {
      echo "missing earlier/later $media buttons: parent=$actions count=${#buttons[@]}" >&2
      call "$actions" org.a11y.atspi.Accessible GetChildren >&2
      jq --arg name "$add_name" '.data[0][] | select(.[6] == $name)' <<< "$cache" >&2
      exit 1
    }
    assert_order() {
      mapfile -t tiles < <(call "$grid" org.a11y.atspi.Accessible GetChildren | jq -r '.data[0][] | .[1]')
      [[ ${#tiles[@]} == ${#expected[@]} ]] || return 1
      for ((k=0;k<${#tiles[@]};k++)); do [[ $(name_of "${tiles[k]}") == "${expected[k]}" ]] || return 1; done
    }
    assert_order
    call "$grid" org.a11y.atspi.Selection SelectChild i 1 >/dev/null
    sleep 0.2
    call "${buttons[2]}" org.a11y.atspi.Action DoAction i 0 >/dev/null
    sleep 0.3
    swap=${expected[0]}; expected[0]=${expected[1]}; expected[1]=$swap
    assert_order
    selected=$(call "$grid" org.a11y.atspi.Selection GetSelectedChild i 0 | jq -r '.data[0][1]')
    [[ $selected == "${tiles[0]}" ]] || { echo "moving $media lost selection" >&2; exit 1; }
    call "${buttons[2]}" org.a11y.atspi.Action DoAction i 0 >/dev/null
    sleep 0.2
    assert_order # moving before the first item must not change the list
    call "${buttons[3]}" org.a11y.atspi.Action DoAction i 0 >/dev/null
    sleep 0.3
    swap=${expected[0]}; expected[0]=${expected[1]}; expected[1]=$swap
    assert_order
    selected=$(call "$grid" org.a11y.atspi.Selection GetSelectedChild i 0 | jq -r '.data[0][1]')
    [[ $selected == "${tiles[1]}" ]] || { echo "moving $media back lost selection" >&2; exit 1; }
    call "$grid" org.a11y.atspi.Selection SelectChild i "$((${#expected[@]} - 1))" >/dev/null
    sleep 0.2
    call "${buttons[3]}" org.a11y.atspi.Action DoAction i 0 >/dev/null
    sleep 0.2
    assert_order # moving after the last item is also a no-op
    call "${buttons[1]}" org.a11y.atspi.Action DoAction i 0 >/dev/null
    sleep 0.3
    unset 'expected[${#expected[@]}-1]'
    assert_order
    echo "PASS: $media ordering and individual removal; remaining references preserved"
    refresh_tree
  done
  clear_all=$(jq -r '.data[0][] | select(.[6] == "Clear all references" and .[7] == 43) | .[0][1]' <<< "$cache")
  call "$clear_all" org.a11y.atspi.Action DoAction i 0 >/dev/null
  sleep 0.3
  refresh_tree
  save=$(jq -r '.data[0][] | select(.[6] == "Save parameters" and .[7] == 43) | .[0][1]' <<< "$cache")
  call "$save" org.a11y.atspi.Action DoAction i 0 >/dev/null
  for ((attempt=0;attempt<30;attempt++)); do
    saved=$(sed -n 's/^mm-air parameters saved=//p' "$scratch/app.out" | tail -1)
    [[ -n $saved && -s $saved ]] && break
    sleep 0.1
  done
  jq -e '.references == [] and .audio_references == []' "$saved" >/dev/null
  while IFS= read -r original; do [[ -f $original ]]; done < <(jq -r '.references[], .audio_references[]' "$MM_AIR_TEST_PARAMETERS")
  roots=$(call /org/a11y/atspi/accessible/root org.a11y.atspi.Accessible GetChildren)
  [[ $(jq '.data[0] | length' <<< "$roots") == 1 ]]
  echo "PASS: clear all removes visual/audio request entries, preserves source files, saves parameters without a filename dialog"
  exit 0
fi
grid=$(jq -r --arg name "$first_name" '
  .data[0] as $items |
  [$items[] | select(.[6] == $name) | .[2][1]] as $parents |
  $items[] | select(.[0][1] as $path | $parents | index($path)) |
  select(.[5] | index("org.a11y.atspi.Selection")) | .[0][1]' <<< "$cache")
[[ -n $grid ]] || { echo "history gallery missing" >&2; exit 1; }
children=$(call "$grid" org.a11y.atspi.Accessible GetChildren)
first=$(jq -r '.data[0][0][1]' <<< "$children")
second=$(jq -r '.data[0][1][1]' <<< "$children")
selected() { call "$grid" org.a11y.atspi.Selection GetSelectedChild i 0 | jq -r '.data[0][1]'; }
mouse 1 1 abs
call "$grid" org.a11y.atspi.Selection SelectChild i 0 >/dev/null
sleep 0.3
[[ $(selected) == "$first" ]] || { echo "explicit initial selection failed" >&2; exit 1; }
# GtkVideo has no accessible name in GTK 4.14, so MM-Air logs each preview it shows.
preview_path() { sed -n 's/^mm-air preview=//p' "$scratch/app.out" | tail -1; }
[[ $(preview_path) == "$first_path" ]] || { echo "native preview did not select the first clip" >&2; exit 1; }
if [[ ${MM_AIR_TEST_IMAGE_REFERENCE:-0} == 1 ]]; then
  cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
  reference_button=$(jq -r '.data[0][] | select(.[6] == "Reference" and .[7] == 43) | .[0][1]' <<< "$cache")
  [[ -n $reference_button ]] || { echo "image reference action missing" >&2; exit 1; }
  call "$reference_button" org.a11y.atspi.Action DoAction i 0 >/dev/null
  sleep 0.5
  # Discover children made visible by the explicit switch to H3 Ref2VA.
  queue=(/org/a11y/atspi/accessible/root)
  for ((j=0;j<${#queue[@]};j++)); do
    [[ $j -lt 512 ]] || exit 1
    mapfile -t descendants < <(call "${queue[j]}" org.a11y.atspi.Accessible GetChildren | jq -r '.data[0][] | .[1]')
    queue+=("${descendants[@]}")
  done
  cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
  jq -e '.data[0][] | select(.[6] == "Selected image added to H3 references; prompt and execution settings were kept")' <<< "$cache" >/dev/null
  reference_grid=$(jq -r --arg name "$first_name" --arg history "$grid" '
    .data[0] as $items | [$items[] | select(.[6] == $name) | .[2][1]] as $parents |
    $items[] | select(.[0][1] as $path | $parents | index($path)) |
    select(.[5] | index("org.a11y.atspi.Selection")) |
    select(.[0][1] != $history) | .[0][1]' <<< "$cache")
  [[ -n $reference_grid ]] || { echo "generated image missing from H3 references" >&2; exit 1; }
  reference_children=$(call "$reference_grid" org.a11y.atspi.Accessible GetChildren)
  [[ $(jq '.data[0] | length' <<< "$reference_children") == 1 ]] || exit 1
  chosen=$(call "$reference_grid" org.a11y.atspi.Selection GetSelectedChild i 0 | jq -r '.data[0][1]')
  [[ $chosen == $(jq -r '.data[0][0][1]' <<< "$reference_children") ]] || exit 1
  echo "PASS: selected image appears in H3 references with its thumbnail and selection; no generation submitted"
  exit 0
fi
# GTK 4.14 reports (0,0) for SCREEN coordinates. WINDOW coordinates retain
# the real tile position; translate them using the actual native X11 origin.
# Source: gtk/4.14.5/gtk/a11y/gtkatspicomponent.c, lines 98-148.
extent=$(call "$second" org.a11y.atspi.Component GetExtents u 1)
window_info=$(xwininfo -name 'MM-AIR · MiniMax H3 Studio')
origin_x=$(awk '/Absolute upper-left X:/ {print $4}' <<< "$window_info")
origin_y=$(awk '/Absolute upper-left Y:/ {print $4}' <<< "$window_info")
[[ -n $origin_x && -n $origin_y ]] || { echo "native window origin unavailable" >&2; exit 1; }
x=$(jq --argjson origin "$origin_x" --argjson scale "$GDK_SCALE" \
  '.data[0] | $origin + $scale * (.[0] + (.[2] / 2 | floor))' <<< "$extent")
y=$(jq --argjson origin "$origin_y" --argjson scale "$GDK_SCALE" \
  '.data[0] | $origin + $scale * (.[1] + (.[3] / 2 | floor))' <<< "$extent")
mouse "$x" "$y" abs
sleep 1.5
[[ $(selected) == "$first" ]] || { echo "FAIL: hovering changed history selection" >&2; exit 1; }
[[ $(preview_path) == "$first_path" ]] || { echo "FAIL: hovering changed the preview clip" >&2; exit 1; }
mouse "$x" "$y" b1c
sleep 0.3
[[ $(selected) == "$second" ]] || {
  echo "FAIL: clicking did not select history item: point=$x,$y extent=$extent selected=$(selected) expected=$second" >&2
  exit 1
}
[[ $(preview_path) == "$second_path" ]] || { echo "FAIL: click did not update the native preview clip" >&2; exit 1; }
echo "PASS: pointer hover preserves selection and preview; one click selects and previews the other clip"
if [[ ${MM_AIR_TEST_COPY_DOWNLOADS:-0} == 1 ]]; then
  cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
  copy_button=$(jq -r '.data[0][] | select(.[6] == "Download" and .[7] == 43) | .[0][1]' <<< "$cache")
  [[ -n $copy_button ]]
  for click in 1 2; do
    call "$copy_button" org.a11y.atspi.Action DoAction i 0 >/dev/null
    for ((attempt=0;attempt<100;attempt++)); do
      [[ $(rg -c '^mm-air copied=' "$scratch/app.out" || true) -ge $click ]] && break
      sleep 0.1
    done
  done
  mapfile -t copied < <(sed -n 's/^mm-air copied=//p' "$scratch/app.out")
  [[ ${#copied[@]} == 2 && ${copied[0]} != "${copied[1]}" ]]
  for destination in "${copied[@]}"; do
    [[ $destination == "$scratch/downloads/"* ]]
    cmp "$second_path" "$destination"
  done
  [[ -f $second_path ]]
  [[ $(preview_path) == "$second_path" ]]
  echo "PASS: Copy to Downloads action copies exact selected media bytes twice, preserves original/preview and avoids overwrite"
fi

if [[ ${MM_AIR_TEST_LAYOUT:-0} == 1 ]]; then
  cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
  edit=$(jq -r '.data[0][] | select((.[6] | startswith("Edit ·")) and .[7] != 29) |
    select(.[5] | index("org.a11y.atspi.Action")) | .[0][1]' <<< "$cache" | head -1)
  [[ -n $edit ]]
  navigation=$(call "$edit" org.a11y.atspi.Component GetExtents u 1)
  echo "navigation=$navigation"
  call "$edit" org.a11y.atspi.Action DoAction i 0 >/dev/null
  sleep 0.5
  queue=(/org/a11y/atspi/accessible/root)
  for ((i=0;i<${#queue[@]};i++)); do
    [[ $i -lt 512 ]] || exit 1
    mapfile -t descendants < <(call "${queue[i]}" org.a11y.atspi.Accessible GetChildren |
      jq -r '.data[0][] | .[1]')
    queue+=("${descendants[@]}")
  done
  cache=$(call /org/a11y/atspi/cache org.a11y.atspi.Cache GetItems)
  for label in "＋ Source image or video" "Edit controls"; do
    panel=$(jq -r --arg label "$label" '.data[0][] | select(.[6] == $label) |
      select(.[7] == (if $label == "Edit controls" then 29 else 43 end)) |
      .[0][1]' <<< "$cache" | head -1)
    [[ -n $panel ]]
    for ((i=0;i<3;i++)); do
      panel=$(busctl --address="$a11y" --json=short get-property "$peer" "$panel"         org.a11y.atspi.Accessible Parent | jq -r '.data[1]')
    done
    extent=$(call "$panel" org.a11y.atspi.Component GetExtents u 1)
    [[ $(jq '.data[0][2]' <<< "$extent") == ${MM_AIR_PANEL_WIDTH:-300} ]]
    echo "PASS: $label panel retains ${MM_AIR_PANEL_WIDTH:-300} px"
  done
  navigation_width=$(jq '.data[0][2]' <<< "$navigation")
  [[ $navigation_width == ${MM_AIR_NAV_WIDTH:-86} ||
     $navigation_width == $((${MM_AIR_NAV_WIDTH:-86} - 1)) ]]
  [[ $(jq '.data[0][3]' <<< "$navigation") == ${MM_AIR_NAV_HEIGHT:-56} ]]
  echo "PASS: configured navigation width and tab height"
fi
