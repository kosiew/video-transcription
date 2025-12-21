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

MODEL = "large-v3-turbo"
HIGH_COMPRESSION = "HIGH_COMPRESSION"

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
    whisper = f"/Users/kosiew/github/whisper.cpp/main  -m /Users/kosiew/GitHub/whisper.cpp/models/ggml-{MODEL}.bin"
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
            default="*.mp4,*.mkv,*.avi",
            help="The pattern to match video files (e.g., '*.mp4', '*.mkv', or '*.avi')",
        ),
    ] = "*.mp4,*.mkv,*.avi",
):
    patterns = file_pattern.split(",")

    file_count = 0
    if os.path.isdir(path_pattern):
        # The path is a directory, process it directly
        folder_path = path_pattern
        for file in os.listdir(folder_path):
            full_file_path = os.path.join(folder_path, file)
            if os.path.isfile(full_file_path):
                maybe_transcribe_video(patterns, folder_path, file_count, file)
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


@app.command()
def sanitize_srt_files(
    folder: Annotated[str, Argument(help="The folder containing srt files to sanitize")],
    min_repetitions: Annotated[int, Option(help="Minimum number of repetitions to consider as spam")] = 3,
    similarity_threshold: Annotated[float, Option(help="Similarity threshold for detecting repetitive text (0.0-1.0)")] = 0.8
):
    """Sanitize SRT files by removing repetitive subtitles that appear for extended periods."""
    file_count = 0
    cleaned_count = 0
    
    for file in os.listdir(folder):
        if file.endswith(".srt"):
            file_path = os.path.join(folder, file)
            if sanitize_srt_file(file_path, min_repetitions, similarity_threshold):
                cleaned_count += 1
            file_count += 1
    
    print(f"==> Processed {file_count} SRT files, cleaned {cleaned_count} files")


def sanitize_srt_file(srt_file: str, min_repetitions: int = 3, similarity_threshold: float = 0.8) -> bool:
    """Sanitize a single SRT file by removing repetitive subtitles."""
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        subtitles = parse_srt_content(content)
        original_count = len(subtitles)
        
        if original_count == 0:
            return False
        
        cleaned_subtitles = remove_repetitive_subtitles(subtitles, min_repetitions, similarity_threshold)
        cleaned_count = len(cleaned_subtitles)
        
        if cleaned_count < original_count:
            # Write the cleaned content back
            cleaned_content = generate_srt_content(cleaned_subtitles)
            with open(srt_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            removed_count = original_count - cleaned_count
            print(f"==> Cleaned {srt_file}: removed {removed_count} repetitive subtitles ({original_count} → {cleaned_count})")
            return True
        
        return False
        
    except Exception as e:
        print(f"==> Error processing {srt_file}: {e}")
        return False


def parse_srt_content(content: str) -> list:
    """Parse SRT content into a list of subtitle dictionaries."""
    subtitles = []
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = int(lines[0])
                timestamp = lines[1]
                text = '\n'.join(lines[2:])
                
                subtitles.append({
                    'index': index,
                    'timestamp': timestamp,
                    'text': text.strip()
                })
            except (ValueError, IndexError):
                continue
    
    return subtitles


def remove_repetitive_subtitles(subtitles: list, min_repetitions: int, similarity_threshold: float) -> list:
    """Remove repetitive subtitles from the list."""
    if len(subtitles) < min_repetitions:
        return subtitles
    
    cleaned_subtitles = []
    i = 0
    
    while i < len(subtitles):
        current_text = normalize_text(subtitles[i]['text'])
        repetition_count = 1
        
        # Check for repetitions starting from current position
        j = i + 1
        while j < len(subtitles) and repetition_count < min_repetitions:
            next_text = normalize_text(subtitles[j]['text'])
            if calculate_similarity(current_text, next_text) >= similarity_threshold:
                repetition_count += 1
                j += 1
            else:
                break
        
        # If we found enough repetitions, skip them all
        if repetition_count >= min_repetitions:
            print(f"    Removing {repetition_count} repetitive subtitles: '{current_text[:50]}...'")
            i = j  # Skip all repetitive subtitles
        else:
            # Keep the current subtitle and move to next
            cleaned_subtitles.append(subtitles[i])
            i += 1
    
    # Reindex the cleaned subtitles
    for idx, subtitle in enumerate(cleaned_subtitles, 1):
        subtitle['index'] = idx
    
    return cleaned_subtitles


def normalize_text(text: str) -> str:
    """Normalize text for comparison by removing extra whitespace and converting to lowercase."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using simple character-based comparison."""
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    
    # Simple character-based similarity
    longer = text1 if len(text1) > len(text2) else text2
    shorter = text2 if len(text1) > len(text2) else text1
    
    if len(longer) == 0:
        return 1.0
    
    # Count matching characters
    matches = sum(c1 == c2 for c1, c2 in zip(shorter, longer))
    return matches / len(longer)


def generate_srt_content(subtitles: list) -> str:
    """Generate SRT content from a list of subtitle dictionaries."""
    content_parts = []
    
    for subtitle in subtitles:
        content_parts.append(f"{subtitle['index']}\n{subtitle['timestamp']}\n{subtitle['text']}\n")
    
    return '\n'.join(content_parts)


@app.command()
def downscale_mkv_folder(
    folder: Annotated[str, Argument(help="The folder containing mkv files to downscale")],
    scale_factor: Annotated[float, Option(help="Scale factor as a percentage (e.g., 50 for 50% = 720p from 1080p)")] = 50,
):
    """Downscale 1080p MKV files to a lower resolution (e.g., 50% -> 720p)."""
    file_count = 0
    converted_count = 0
    
    for file in os.listdir(folder):
        if file.endswith(".mkv"):
            file_path = os.path.join(folder, file)
            if downscale_mkv_file(file_path, scale_factor):
                converted_count += 1
            file_count += 1
    
    print(f"==> Processed {file_count} MKV files, converted {converted_count} files")


def downscale_mkv_file(mkv_file: str, scale_factor: int = 50, compression: str = HIGH_COMPRESSION) -> bool:
    """Downscale a single MKV file to a lower resolution."""
    try:
        # Calculate target resolution
        # 1080p = 1920x1080, scale to percentage
        scale_percent = scale_factor / 100
        target_width = int(1920 * scale_percent)
        target_height = int(1080 * scale_percent)
        
        # Ensure dimensions are even (required for many codecs)
        target_width = target_width if target_width % 2 == 0 else target_width - 1
        target_height = target_height if target_height % 2 == 0 else target_height - 1
        
        # Create output filename with _downscaled suffix
        base_path = os.path.splitext(mkv_file)[0]
        output_file = f"{base_path}_downscaled.mkv"
        
        # Check if output already exists
        if os.path.exists(output_file):
            print(f"==> {output_file} already exists, skipping")
            return False
        
        # FFmpeg command to downscale video - faster
        ffmpeg_command = f'ffmpeg -i "{mkv_file}" -vf scale={target_width}:{target_height} -c:a copy "{output_file}"'
        if compression == HIGH_COMPRESSION:
            # FFmpeg command to downscale video - slower for higher compression
            ffmpeg_command = f'ffmpeg -i "{mkv_file}" -vf scale={target_width}:{target_height} -c:v libx264 -crf 20 -preset slow -c:a copy "{output_file}"'
        
        print(f"==> Downscaling {mkv_file} to {target_width}x{target_height}")
        result = subprocess.run(ffmpeg_command, shell=True, capture_output=True)
        
        if result.returncode == 0:
            print(f"==> Successfully converted to {output_file}")
            return True
        else:
            print(f"==> Error converting {mkv_file}: {result.stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"==> Error processing {mkv_file}: {e}")
        return False


if __name__ == "__main__":
    app()
