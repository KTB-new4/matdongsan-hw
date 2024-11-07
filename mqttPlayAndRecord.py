# pip install paho-mqtt==1.6.1 requests sounddevice soundfile pygame numpy

import paho.mqtt.client as mqtt
import requests
import sounddevice as sd
import soundfile as sf
import pygame
import tempfile
import os

# MQTT 브로커 주소와 구독할 토픽 설정
BROKER_ADDRESS = "test.mosquitto.org"
TOPIC = "devices/raspberry_pi/command"

# MQTT 메시지를 수신할 때 실행되는 콜백 함수
def on_message(client, userdata, message):
    command = message.payload.decode("utf-8")
    print(f"Received command: {command}")
    
    # 명령 형식이 "play-and-record <url>"인지 확인
    if command.startswith("play-and-record"):
        url = command.split(" ")[1]
        play_and_record(url)

# 오디오를 재생하고 녹음하는 함수
def play_and_record(url):
    # 1. URL에서 오디오 파일 다운로드
    response = requests.get(url)

    # 2. 오디오 파일을 임시 mp3 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        temp_file.write(response.content)
        temp_file.flush()

        # 3. mp3 파일을 wav 파일로 변환 (pygame이 wav 형식을 더 안정적으로 재생할 수 있음)
        wav_file = temp_file.name.replace(".mp3", ".wav")
        os.system(f"ffmpeg -i {temp_file.name} {wav_file}")

        # 4. 변환된 wav 파일을 재생
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(wav_file)
            print("Playing audio...")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():  # 재생이 끝날 때까지 대기
                continue
            print("Audio playback finished.")
        except Exception as e:
            print(f"Audio playback failed: {e}")
        finally:
            # 임시 파일 삭제
            os.remove(temp_file.name)
            os.remove(wav_file)

    # 녹음 파일을 저장할 경로 설정
    # wav_filename = "./recorded_audio.wav"
    # mp3_filename = "./recorded_audio.mp3"

    # 오디오 녹음 및 MP3로 변환
    # record_audio(wav_filename, duration=10)
    # convert_to_mp3(wav_filename, mp3_filename)

# 오디오를 녹음하여 파일로 저장하는 함수
# def record_audio(filename, duration=10, sample_rate=44100):
#     print("Recording...")
#     recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
#     sd.wait()  # 녹음이 완료될 때까지 대기
#     print("Recording complete.")
#     sf.write(filename, recording, sample_rate)  # 녹음을 WAV 파일로 저장

# WAV 파일을 MP3로 변환하는 함수
# def convert_to_mp3(wav_filename, mp3_filename):
#     print("Converting WAV to MP3...")
#     os.system(f"ffmpeg -i {wav_filename} {mp3_filename}")
#     os.remove(wav_filename)  # 변환 후 원본 WAV 파일 삭제
#     print(f"Conversion complete. Saved as {mp3_filename}")

print("정상실행확인...")

# MQTT 클라이언트 설정
client = mqtt.Client("RaspberryPi")
client.on_message = on_message

# MQTT 브로커에 연결
print("Connecting to MQTT broker...")
client.connect(BROKER_ADDRESS)

# 특정 토픽 구독
print(f"Subscribing to topic: {TOPIC}")
client.subscribe(TOPIC)

# 메시지 수신 대기
print("Waiting for messages...")
client.loop_forever()
