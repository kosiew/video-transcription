import fnmatch
import os
import re
import subprocess
from datetime import timedelta
from shlex import join
from typing import Annotated, Optional

from numpy import full, short
from rich import print
from typer import Argument, Option, Typer

# requires /Users/kosiew/GitHub/whisper.cpp and ffmpeg, the above
# imports
app = Typer()

# sample srt file name Harry Wild - S01E02 - Samurai Plague Doctor Kills for Kicks.srt
# regex pattern to extract the season and episode number
pattern = r"S(\d{2})E(\d{2})"
regex = re.compile(pattern, re.IGNORECASE)


@app.command()
def extract_wav(
    input_video: Annotated[str, Argument(help="The path to the input video file")]
) -> str:  # get wav filename from input video

    wav_file = get_wav_filename(input_video)
    extract_wav_command = f'ffmpeg -i "{input_video}" -ac 1 -ar 16000 "{wav_file}"'
    print(f"==> Extracting audio to {wav_file}")
    subprocess.run(extract_wav_command, shell=True)
    return wav_file


def get_wav_filename(input_video):
    short_filename_without_extension = shorten_filename(input_video)
    wav_file = short_filename_without_extension + ".wav"
    return wav_file


@app.command()
def transcribe_wav(
    wav_file: Annotated[str, Argument(help="The path to the .wav file to transcribe")]
) -> str:
    whisper = "/Users/kosiew/github/whisper.cpp/main  -m /Users/kosiew/GitHub/whisper.cpp/models/ggml-large-v2.bin"
    whisper_command = f'{whisper} -osrt -f "{wav_file}"'

    print(f"==> Transcribing audio from {wav_file}")
    subprocess.run(whisper_command, shell=True)

    srt_file = rename_wav_to_srt(wav_file)
    return srt_file


def rename_wav_to_srt(wav_file):
    wav_srt_file, srt_file = get_wav_srt_filename(wav_file)
    # rename srt file, remove .wav from filename
    print(f"==> Renaming {wav_srt_file} to {srt_file}")
    os.rename(wav_srt_file, srt_file)
    return srt_file


def get_wav_srt_filename(wav_file):
    wav_srt_file = f"{wav_file}.srt"
    srt_file = wav_srt_file.replace(".wav", "")
    return wav_srt_file, srt_file


@app.command()
def transcribe_video(
    input_video: Annotated[str, Argument(help="The path to the input video file")]
) -> Optional[str]:
    already_transcribed = check_whether_transcribed(input_video)

    if already_transcribed:
        print(f"==> {input_video} already transcribed, skipping")
        return None
    else:
        wav_file = extract_wav(input_video)
        srt_file = transcribe_wav(wav_file)
        print(f"==> Removing {wav_file}")
        os.remove(wav_file)
        return srt_file


def check_whether_transcribed(input_video):
    _wav_file = get_wav_filename(input_video)
    _, _srt_file = get_wav_srt_filename(_wav_file)
    already_transcribed = os.path.exists(_srt_file)
    return already_transcribed


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
    path_pattern: Annotated[
        str, Argument(help="The path to the folder with video files")
    ],
    file_pattern: Annotated[
        str,
        Option(
            default="*.mp4,*.mkv",
            help="The pattern to match video files (e.g., '*.mp4' or '*.mkv')",
        ),
    ] = "*.mp4,*.mkv",
):
    patterns = file_pattern.split(",")

    file_count = 0
    if os.path.isdir(path_pattern):
        # The path is a directory, process it directly
        folder_path = path_pattern
        for file in os.listdir(folder_path):
            full_file_path = os.path.join(folder_path, file)
            if os.path.isfile(full_file_path):
                if any(fnmatch.fnmatch(file, pattern) for pattern in patterns):
                    srt_file = transcribe_video(full_file_path)
                    if srt_file:
                        print(f"==> Transcribed {file} to {srt_file}")
                        file_count += 1
            else:
                file_count += transcribe_folder(full_file_path, file_pattern)
    else:
        base_folder = os.path.dirname(path_pattern)
        folder_pattern = os.path.basename(path_pattern)
        for folder in os.listdir(base_folder):
            folder_path = os.path.join(base_folder, folder)
            is_dir = os.path.isdir(folder_path)
            if is_dir and fnmatch.fnmatch(folder, folder_pattern):
                file_count += transcribe_folder(folder_path, file_pattern)
    print(f"==> Transcribed {file_count} files")
    return file_count


def maybe_transcribe_video(patterns, folder_path, file_count, file):
    full_file_path = os.path.join(folder_path, file)
    if os.path.isfile(full_file_path):
        if any(fnmatch.fnmatch(file, pattern) for pattern in patterns):
            srt_file = transcribe_video(full_file_path)
            if srt_file:
                print(f"==> Transcribed {file} to {srt_file}")
                file_count += 1


if __name__ == "__main__":
    app()
