import sys
import os
from pytube import YouTube
from pydub import AudioSegment
from bs4 import BeautifulSoup
import requests 
from youtubesearchpython import VideosSearch
import yt_dlp
import re
import random
import shutil

def get_unique_video_url(singer_name, num_videos):
    query = f"{singer_name} songs"
    search_url = f"https://www.youtube.com/results?search_query={query}"

    response = requests.get(search_url)
    html_content = response.text

    video_ids = re.findall(r'watch\?v=(\S{11})', html_content)

    if len(video_ids) < num_videos:
        print(f"Error during video fetching: not enough videos found for {singer_name}.")
        sys.exit(1)

    unique_video_ids = random.sample(video_ids, num_videos)
    video_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in unique_video_ids]

    return video_urls


def create_directory(directory):
    # Function to create a directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_videos(singer_name, num_videos):
    download_path = os.path.join(os.getcwd(), "downloads")
    create_directory(download_path)

    print(f"Downloading {num_videos} random videos of {singer_name} from YouTube...")

    downloaded_count = 0
    retry_limit = 2

    try:
        video_urls = get_unique_video_url(singer_name, num_videos)

        for video_url in video_urls:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(download_path, f'video{downloaded_count + 1}.%(ext)s'),
                'max_duration': 250, 
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])

                downloaded_count += 1
                print(f"Downloaded video{downloaded_count}")

            except yt_dlp.DownloadError as e:
                print(f"Error during video download: {str(e)}")
                for retry in range(retry_limit):
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([video_url])

                        downloaded_count += 1
                        print(f"Downloaded video{downloaded_count} (after retry {retry + 1})")
                        break

                    except yt_dlp.DownloadError:
                        print(f"Retry {retry + 1} failed.")
                        if retry == retry_limit - 1:
                            print("Maximum retries reached. Skipping this video.")

        print(f"\nTotal videos downloaded: {downloaded_count}")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


def convert_to_audio(num_videos):
    download_path = os.path.join(os.getcwd(), "downloads")
    create_directory(download_path)
    audio_path = os.path.join(os.getcwd(), "audio")
    create_directory(audio_path)

    print("Converting videos to audio...")
    for i in range(1, num_videos + 1):
        video_file = os.path.join(download_path, f"video{i}.webm")
        audio_file = os.path.join(audio_path, f"audio{i}.wav")

        print(f"Converting {video_file} to {audio_file}...")

        # Check if the video file exists before converting
        if os.path.exists(video_file):
            video = AudioSegment.from_file(video_file, format="webm")
            video.export(audio_file, format="wav")
            print(f"Conversion completed for {video_file}")
        else:
            print(f"Error: {video_file} not found.")


def cut_audio(num_videos, audio_duration):
    audio_path = os.path.join(os.getcwd(), "audio") 
    create_directory(audio_path)

    for i in range(1, num_videos + 1):
        input_file = os.path.join(audio_path, f'audio{i}.wav')
        output_file = os.path.join(audio_path, f'cut_audio{i}.wav')

        audio = AudioSegment.from_wav(input_file)
        cut_audio = audio[:audio_duration * 1000]

        print(f"Cutting first {audio_duration} seconds from {input_file}...")

        try:
            cut_audio.export(output_file, format="wav")
            print(f"Audio cut successfully. Output saved to {output_file}")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            sys.exit(1)

def merge_audios(output_file, num_files):
    audio_path = os.path.join(os.getcwd(), "audio") 
    create_directory(audio_path)

    combined_audio = AudioSegment.silent(duration=0) 

    for i in range(1, num_files + 1):
        input_file = os.path.join(audio_path, f'cut_audio{i}.wav')

        try:
            audio = AudioSegment.from_wav(input_file)
            combined_audio += audio  
        except Exception as e:
            print(f"An error occurred while merging cut audio: {str(e)}")
            sys.exit(1)

    try:
        combined_audio.export(output_file, format="wav")
        print(f"All cut audios merged successfully. Output saved to {output_file}")
    except Exception as e:
        print(f"An error occurred while exporting merged audio: {str(e)}")
        sys.exit(1)

def main():
    # Check if correct number of parameters are provided
    if len(sys.argv) != 5:
        print("Usage: python <program.py> <SingerName> <NumberOfVideos> <AudioDuration> <OutputFileName>")
        sys.exit(1)

    try:
        singer_name = sys.argv[1].strip()
        num_videos = int(sys.argv[2])
        audio_duration = int(sys.argv[3])
        output_file_name = sys.argv[4]

        download_videos(singer_name, num_videos)

        convert_to_audio(num_videos)

        cut_audio(num_videos, audio_duration)

        output_file = os.path.join(os.getcwd(), output_file_name)

        # Merge audio files
        merge_audios(output_file, num_videos)

        print(f"Mashup completed successfully! Output saved as {output_file}")

    except ValueError:
        print("Invalid input. Please provide valid numeric values for NumberOfVideos and AudioDuration.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()