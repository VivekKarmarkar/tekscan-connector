#!/usr/bin/env bash
# DRAFT of the standalone Tekscan project video. Combines:
#   Part 1 — the instructional/assembly guide (tekscan_assembly_guide.mp4, 1920x1080)
#   Part 2 — the live demo explainer (tekscan_explainer.mp4, 1920x720, letterboxed)
# with a title card, section dividers, and a "more to come" outro stub.
# Common canvas 1920x1080 / 30 fps / H.264 + AAC. Re-encode once at the concat.
set -euo pipefail
ROOT="/home/vivekkarmarkar/Python Files/tekscan-connector"
W="$ROOT/video/proj_tmp"; mkdir -p "$W"
FB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BG="0x0d1117"; GREEN="0x7ee787"; GRAY="0x8b949e"
ASM="$ROOT/tekscan_assembly_guide.mp4"
EXP="$ROOT/tekscan_explainer.mp4"
OUTF="$ROOT/tekscan_project_draft.mp4"

card () { # $1 out  $2 dur  then drawtext args via $3 (filter string)
  ffmpeg -y -f lavfi -i "color=c=${BG}:s=1920x1080:d=$2:r=30" \
    -f lavfi -i "anullsrc=cl=stereo:r=44100" \
    -filter_complex "[0:v]$3,format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st=$(echo "$2-0.5"|bc):d=0.5[v]" \
    -map "[v]" -map 1:a -t "$2" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 44100 -ac 2 "$1"
}

card "$W/c_title.mp4" 4.0 "
  drawtext=fontfile=${FB}:text='TEKSCAN FLEXIFORCE':fontcolor=${GREEN}:fontsize=92:x=(w-text_w)/2:y=380:
  shadowcolor=black:shadowx=2:shadowy=2,
  drawtext=fontfile=${FB}:text='Live Force on Linux':fontcolor=white:fontsize=58:x=(w-text_w)/2:y=508,
  drawtext=fontfile=${FB}:text='reverse-engineered — no Windows, no vendor SDK':fontcolor=${GRAY}:fontsize=32:x=(w-text_w)/2:y=600"

card "$W/c_part1.mp4" 2.8 "
  drawtext=fontfile=${FB}:text='PART ONE':fontcolor=${GRAY}:fontsize=40:x=(w-text_w)/2:y=448,
  drawtext=fontfile=${FB}:text='Setup & Assembly':fontcolor=white:fontsize=78:x=(w-text_w)/2:y=512"

card "$W/c_part2.mp4" 2.8 "
  drawtext=fontfile=${FB}:text='PART TWO':fontcolor=${GRAY}:fontsize=40:x=(w-text_w)/2:y=448,
  drawtext=fontfile=${FB}:text='Live Demo, Decoded':fontcolor=white:fontsize=78:x=(w-text_w)/2:y=512"

card "$W/c_outro.mp4" 4.0 "
  drawtext=fontfile=${FB}:text='MORE TO COME':fontcolor=${GREEN}:fontsize=72:x=(w-text_w)/2:y=420,
  drawtext=fontfile=${FB}:text='calibration · multi-sensor · your ideas':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=540,
  drawtext=fontfile=${FB}:text='(draft — section order & content to be discussed)':fontcolor=${GRAY}:fontsize=28:x=(w-text_w)/2:y=620"

echo "=== cards built; normalizing the two parts to 1920x1080 ==="
# Part 1: already 1080; normalize params. Part 2: pad 720 -> 1080 (centered).
ffmpeg -y -i "$ASM" -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30,format=yuv420p,setsar=1" \
  -af "aformat=sample_rates=44100:channel_layouts=stereo" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 44100 -ac 2 "$W/part1.mp4"
ffmpeg -y -i "$EXP" -vf "scale=1920:720,pad=1920:1080:0:180:black,fps=30,format=yuv420p,setsar=1" \
  -af "aformat=sample_rates=44100:channel_layouts=stereo" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 44100 -ac 2 "$W/part2.mp4"

echo "=== concat all 6 pieces ==="
ffmpeg -y -i "$W/c_title.mp4" -i "$W/c_part1.mp4" -i "$W/part1.mp4" -i "$W/c_part2.mp4" -i "$W/part2.mp4" -i "$W/c_outro.mp4" \
  -filter_complex "
   [0:v][0:a][1:v][1:a][2:v][2:a][3:v][3:a][4:v][4:a][5:v][5:a]concat=n=6:v=1:a=1[v][a]
  " -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 44100 -ac 2 -movflags +faststart "$OUTF"

echo "=== PROJECT DRAFT ==="
ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name,width,height -of default=noprint_wrappers=1 "$OUTF"
