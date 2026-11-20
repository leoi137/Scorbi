#!/bin/sh
# Lay the frames media/render.py wrote over a studio backdrop, then write
# media/scorbi-turntable.gif (the README's turntable) and media/scorbi.png (a still).
#
#   sh media/make_gif.sh <dir>     # <dir> holds anim/ (96 frames) and hero/ (frame 0)
set -e
DIR=$1
MEDIA=$(cd "$(dirname "$0")" && pwd)

# a dark backdrop, a little lighter behind the robot
G='exp(-(pow((X-W*0.5)/(W*0.42),2)+pow((Y-H*0.62)/(H*0.55),2)))'
backdrop() {
  ffmpeg -v error -y -f lavfi -i "color=c=black:s=$1,format=rgb24,geq=r='18+26*$G':g='20+29*$G':b='23+33*$G'" -frames:v 1 "$2"
}
backdrop 960x640 "$DIR/bg_anim.png"
backdrop 1800x1200 "$DIR/bg_hero.png"

ffmpeg -v error -y -i "$DIR/bg_hero.png" -i "$DIR/hero/frame_0000.png" \
  -filter_complex "[0][1]overlay=format=auto,scale=1440:-1:flags=lanczos" "$MEDIA/scorbi.png"

ffmpeg -v error -y -loop 1 -framerate 24 -i "$DIR/bg_anim.png" -framerate 24 -i "$DIR/anim/frame_%04d.png" \
  -filter_complex "[0][1]overlay=format=auto:shortest=1,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle" \
  -loop 0 "$MEDIA/scorbi-turntable.gif"

ls -l "$MEDIA/scorbi.png" "$MEDIA/scorbi-turntable.gif"
