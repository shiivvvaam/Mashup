from flask import Flask, render_template, request, jsonify
import smtplib
import zipfile
from email.message import EmailMessage
from io import BytesIO
import os
from pytube import YouTube
from pydub import AudioSegment
from bs4 import BeautifulSoup
import requests
import yt_dlp
import re
import random
import shutil

# Initialize Flask app
app = Flask(__name__)

# Function to download videos from YouTube
def download_videos(singer_name, num_videos, output_dir):
    query = f"{singer_name} songs"
    search_url = f"https://www.youtube.com/results?search_query={query}"

    response = requests.get(search_url)
    html_content = response.text

    video_ids = re.findall(r'watch\?v=(\S{11})', html_content)

    if len(video_ids) < num_videos:
        raise ValueError(f"Not enough videos found for {singer_name}.")

    unique_video_ids = random.sample(video_ids, num_videos)
    video_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in unique_video_ids]

    for i, video_url in enumerate(video_urls):
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(output_dir, f'video{i + 1}.webm'),
                'max_duration': 250,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

        except yt_dlp.DownloadError as e:
            raise ValueError(f"Error downloading video {i + 1}: {str(e)}")

# Function to convert videos to audio
def convert_to_audio(num_videos, input_dir, output_dir):
    for i in range(num_videos):
        video_file = os.path.join(input_dir, f"video{i + 1}.webm")
        audio_file = os.path.join(output_dir, f"audio{i + 1}.wav")

        if os.path.exists(video_file):
            video = AudioSegment.from_file(video_file, format="webm")
            video.export(audio_file, format="wav")

# Function to cut audio files
def cut_audio(num_videos, audio_duration, input_dir, output_dir):
    for i in range(num_videos):
        input_file = os.path.join(input_dir, f'audio{i + 1}.wav')
        output_file = os.path.join(output_dir, f'cut_audio{i + 1}.wav')

        audio = AudioSegment.from_wav(input_file)
        cut_audio = audio[:audio_duration * 1000]  # Cut the first 'audio_duration' seconds

        cut_audio.export(output_file, format="wav")

# Function to merge audio files
def merge_audios(num_files, input_dir, output_file):
    combined_audio = AudioSegment.silent(duration=0)  # Initialize an empty audio segment

    for i in range(num_files):
        input_file = os.path.join(input_dir, f'cut_audio{i + 1}.wav')

        audio = AudioSegment.from_wav(input_file)
        combined_audio += audio  # Concatenate the cut audio segments

    combined_audio.export(output_file, format="wav")

# Function to send email with the result zip file
def send_email(email, zip_data):
    try:
        # Compose email
        msg = EmailMessage()
        msg['From'] = 'himanshu@gmail.com'
        msg['To'] = email
        msg['Subject'] = 'Mashup Result'

        # Attach zip file
        msg.add_attachment(zip_data, maintype='application', subtype='zip', filename='mashup_result.zip')

        # Send email
        with smtplib.SMTP('smtp.example.com', 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login('your_email@example.com', 'your_password')
            smtp.send_message(msg)

        return True

    except Exception as e:
        raise ValueError(f"Error sending email: {str(e)}")

# Function to process mashup
def process_mashup(singer_name, num_videos, audio_duration, email):
    # Create directories for storing intermediate files
    temp_dir = os.path.join(os.getcwd(), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    download_dir = os.path.join(temp_dir, 'download')
    audio_dir = os.path.join(temp_dir, 'audio')
    
    os.makedirs(audio_dir, exist_ok=True)

    try:
        # Download videos
        download_videos(singer_name, num_videos, download_dir)

        # Convert videos to audio
        convert_to_audio(num_videos, download_dir, audio_dir)

        # Cut audio files
        cut_audio(num_videos, audio_duration, audio_dir, audio_dir)

        # Merge audio files
        output_file = os.path.join(temp_dir, 'output.wav')
        merge_audios(num_videos, audio_dir, output_file)

        # Package result into a zip file
        with BytesIO() as buffer:
            with zipfile.ZipFile(buffer, 'w') as zipf:
                zipf.write(output_file, os.path.basename(output_file))

            buffer.seek(0)
            zip_data = buffer.getvalue()

        # Send the zip file via email
        send_email(email, zip_data)

        return True

    except Exception as e:
        raise ValueError(f"Mashup processing failed: {str(e)}")

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

# Route to serve HTML form
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle mashup requests
@app.route('/mashup', methods=['POST'])
def mashup():
    try:
        # Get parameters from the form submission
        singer_name = request.form['singer_name']
        num_videos = int(request.form['num_videos'])
        audio_duration = int(request.form['audio_duration'])
        email = request.form['email']

        # Process the mashup
        process_mashup(singer_name, num_videos, audio_duration, email)

        return jsonify({'message': 'Mashup request processed successfully. Result will be sent to your email.'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
