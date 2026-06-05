#!/usr/bin/env bash
# Composite the assembly guide: each slide is held for the duration of its
# narration clip (+ a breath), with gentle fades, then all segments concatenate.
set -e
ROOT="/home/vivekkarmarkar/Python Files/tekscan-connector"
SLIDES="$ROOT/video/slides"
AUDIO="$ROOT/video/audio"
WORK="$ROOT/video/work"
mkdir -p "$WORK"

# Narration files, oldest-first == segment order (they were generated in order).
mapfile -t AUD < <(ls -tr "$AUDIO"/tts_*.mp3)
echo "audio order:"; printf '  %s\n' "${AUD[@]}"
[ "${#AUD[@]}" -eq 6 ] || { echo "expected 6 audio files, got ${#AUD[@]}"; exit 1; }

LIST="$WORK/concat.txt"; : > "$LIST"
for i in 1 2 3 4 5 6; do
  slide="$SLIDES/slide_0${i}.png"
  audio="${AUD[$((i-1))]}"
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$audio")
  total=$(awk "BEGIN{printf \"%.3f\", $dur + 1.0}")
  fout=$(awk "BEGIN{printf \"%.3f\", $dur + 1.0 - 0.35}")
  seg="$WORK/seg_0${i}.mp4"
  ffmpeg -y -hide_banner -loglevel error \
    -loop 1 -framerate 30 -i "$slide" -i "$audio" \
    -filter_complex "[0:v]scale=1920:1080,setsar=1,format=yuv420p,fade=t=in:st=0:d=0.35,fade=t=out:st=${fout}:d=0.35[v];[1:a]adelay=250|250,apad=pad_dur=0.7,aresample=44100[a]" \
    -map "[v]" -map "[a]" -t "$total" \
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 44100 "$seg"
  echo "file '$seg'" >> "$LIST"
  printf "  seg %d: narration=%.2fs slide=%.2fs\n" "$i" "$dur" "$total"
done

OUT="$ROOT/tekscan_assembly_guide.mp4"
ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i "$LIST" -c copy "$OUT" 2>/dev/null \
  || ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i "$LIST" \
       -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k "$OUT"

echo "=== FINAL ==="
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1:nokey=0 "$OUT"
echo "$OUT"
