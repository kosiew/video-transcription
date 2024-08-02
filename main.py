import os
import re
import subprocess
from datetime import timedelta
from typing import Annotated

import typer
from numpy import short
from rich import print
from typer import Argument

# requires /Users/kosiew/GitHub/whisper.cpp and ffmpeg, the above
# imports  
app = typer.Typer()

# sample srt file name Harry Wild - S01E02 - Samurai Plague Doctor Kills for Kicks.srt
# regex pattern to extract the season and episode number
pattern = r"S(\d{2})E(\d{2})"
regex = re.compile(pattern, re.IGNORECASE)


@app.command()
def extract_wav(
    input_video: Annotated[str, Argument(help="The path to the input video file")]
) -> str:  # get wav filename from input video

    short_filename_without_extension = shorten_filename(input_video)
    wav_file = short_filename_without_extension + ".wav"
    extract_wav_command = f'ffmpeg -i "{input_video}" -ac 1 -ar 16000 "{wav_file}"'
    print(f"==> Extracting audio to {wav_file}")
    subprocess.run(extract_wav_command, shell=True)
    return wav_file


@app.command()
def transcribe_wav(
    wav_file: Annotated[str, Argument(help="The path to the .wav file to transcribe")]
) -> str:
    whisper = "/Users/kosiew/github/whisper.cpp/main  -m /Users/kosiew/GitHub/whisper.cpp/models/ggml-large-v2.bin"
    whisper_command = f'{whisper} -osrt -f "{wav_file}"'

    print(f"==> Transcribing audio from {wav_file}")
    subprocess.run(whisper_command, shell=True)

    wav_srt_file = f"{wav_file}.srt"
    srt_file = wav_srt_file.replace(".wav", "")
    # rename srt file, remove .wav from filename
    print(f"==> Renaming {wav_srt_file} to {srt_file}")
    os.rename(wav_srt_file, srt_file)
    return srt_file


@app.command()
def transcribe_video(
    input_video: Annotated[str, Argument(help="The path to the input video file")]
) -> str:
    wav_file = extract_wav(input_video)
    srt_file = transcribe_wav(wav_file)
    # remove wav file
    print(f"==> Removing {wav_file}")
    os.remove(wav_file)
    return srt_file


def shorten_filename(filepath: str) -> str:
    # eg shorten /Volumes/F/Movies/Harry Wild/Season 1/Harry Wild - S01E02 - Samurai Plague Doctor Kills for Kicks
    # to /Volumes/F/Movies/Harry Wild/Season 1/S01E02

    filepath_without_extension = os.path.splitext(filepath)[0]
    global regex
    match = regex.search(filepath_without_extension)

    short_filename = filepath_without_extension

    # use regex replace
    if match:
        season = match.group(1)
        episode = match.group(2)
        _short_filename = f"S{season}E{episode}"
        # join folder to short_filename
        folder = os.path.dirname(filepath_without_extension)
        short_filename = os.path.join(folder, _short_filename)

    return short_filename


def shorten_srt_filename(srt_file: str) -> str:
    # eg shorten /Volumes/F/Movies/Harry Wild/Season 1/Harry Wild - S01E02 - Samurai Plague Doctor Kills for Kicks.srt
    # to /Volumes/F/Movies/Harry Wild/Season 1/S01E02.srt

    short_filepath = shorten_filename(srt_file) + ".srt"

    return short_filepath


@app.command()
def rename_to_short_srt_filename_in_folder(
    folder: Annotated[str, Argument(help="The folder the srt files")]
):
    file_count = 0
    for file in os.listdir(folder):
        if file.endswith(".srt"):
            rename_to_short_srt_filename(os.path.join(folder, file))
            file_count += 1
    print(f"==> Renamed {file_count} files")


@app.command()
def rename_to_short_srt_filename(
    srt_file: Annotated[str, Argument(help="The path to the srt file")]
):
    short_filename = shorten_srt_filename(srt_file)
    if short_filename != srt_file:
        os.rename(srt_file, short_filename)
        print(f"==> Renamed {srt_file} to {short_filename}")


@app.command()
def transcribe_folder(
    folder: Annotated[str, Argument(help="The path to the folder with video files")]
):
    file_count = 0
    for file in os.listdir(folder):
        if file.endswith(".mp4") or file.endswith(".mkv"):
            srt_file = transcribe_video(os.path.join(folder, file))
            print(f"==> Transcribed {file} to {srt_file}")
            file_count += 1
    print(f"==> Transcribed {file_count} files")


if __name__ == "__main__":
    app()
