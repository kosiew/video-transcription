import os
import subprocess
from datetime import timedelta
from typing import Annotated

import typer
from rich import print
from typer import Argument

app = typer.Typer()


@app.command()
def extract_wav(
    input_video: Annotated[str, Argument(help="The path to the input video file")]
) -> str:  # get wav filename from input video
    filename_without_extension = os.path.splitext(input_video)[0]
    wav_file = filename_without_extension + ".wav"
    extract_wav_command = f'ffmpeg -i "{input_video}" -ac 1 -ar 16000 "{wav_file}"'
    print(f"Extracting audio to {wav_file}")
    subprocess.run(extract_wav_command, shell=True)
    return wav_file


@app.command()
def transcribe_wav(
    wav_file: Annotated[str, Argument(help="The path to the .wav file to transcribe")]
) -> str:
    whisper = "/Users/kosiew/github/whisper.cpp/main  -m /Users/kosiew/GitHub/whisper.cpp/models/ggml-large-v2.bin"
    whisper_command = f'{whisper} -osrt -f "{wav_file}"'
    print(f"Transcribing audio from {wav_file}")
    subprocess.run(whisper_command, shell=True)
    wav_srt_file = f"{wav_file}.srt"
    # rename to remove .wav
    srt_file = wav_srt_file.replace(".wav", "")
    # os rename the file
    os.rename(wav_srt_file, srt_file)
    return srt_file


@app.command()
def transcribe_video(
    input_video: Annotated[str, Argument(help="The path to the input video file")]
) -> str:
    wav_file = extract_wav(input_video)
    srt_file = transcribe_wav(wav_file)
    # delete wav file
    os.remove(wav_file)
    return srt_file


# not required
def add_srt_to_video(input_video, subtitles_file, output_file):

    # FFmpeg command
    ffmpeg_command = f"""ffmpeg -i {input_video} -vf "subtitles={subtitles_file}:force_style='FontName=Arial,FontSize=10,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=3,Outline=1,Shadow=1,Alignment=2,MarginV=10'" -c:a copy {output_file} -y """

    # Run the FFmpeg command
    subprocess.run(ffmpeg_command, shell=True)

    input_video_path = "input.mp4"
    output_file = "output.mp4"
    transcribe_video(input_video_path)
    add_srt_to_video(input_video_path, output_file)


@app.command()
def transcribe_folder(
    folder: Annotated[str, Argument(help="The path to the folder with video files")]
):
    for file in os.listdir(folder):
        if file.endswith(".mp4") or file.endswith(".mkv"):
            srt_file = transcribe_video(os.path.join(folder, file))
            print(f"Transcribed {file} to {srt_file}")


if __name__ == "__main__":
    app()
