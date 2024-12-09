# pip install paho-mqtt==1.6.1 requests sounddevice soundfile pygame numpy

# 테스트할 땐 vscode의 터미널로 실행해야 녹음이 가능 
# 재생이 완료되면 특정 시간동안 오디오를 입력받아 녹음하고 원래의 스프링으로 보내줘야함.
# 오디오를 녹음하고 파일로 저장해 AWS의 S3에 업로드하고 해당 링크를 스프링에 전달하거나 녹음 파일 자체를 스프링에게 넘겨주는 방식을 사용해야함.
# 이렇게 오디오를 넘겨주면 다시 그에 대한 출력을 위의 오디오 재생 로직을 재사용하면 될듯. -> 종료하려면 특정 버튼을 클릭하거나 음성을 입력받는 식으로 진행
# 오디오를 녹음할 때 특정 데시벨을 넘기는 경우에만 녹음을 하고 특정 데시벨 이하로 얼마간 지속되면 그때 녹음을 종료하고 스프링으로 전달해야함.
# 또한 오디오를 재생할 때 오디오를 조작할 수 있어야함. (아마도 휴대폰 앱을 사용해 조작할듯. 그럼 그 조작을 다시 MQTT로 전달받아 그걸 사용?) -> 싱크나 이런게 안맞을 가능성

# 메시지큐를 사용하기 때문에 여러번 입력이 들어오면 큐에 들어가 대기 상태로 들어감. 따라서 중복 요청을 처리할 코드 작성이 필요할듯.

import paho.mqtt.client as mqtt
import requests
import sounddevice as sd
import soundfile as sf
import pygame
import tempfile
import os
import threading
import time

# MQTT 브로커 주소와 구독할 토픽 설정
BROKER_ADDRESS = "52.78.46.251"
TOPIC = "devices/raspberry_pi/command"
SPRING_BACKEND_URL = "http://localhost:8080/upload"  # 스프링 백엔드 파일 업로드 엔드포인트

# MQTT 메시지를 수신할 때 실행되는 콜백 함수
def on_message(client, userdata, message):
    print(f"Received message: Topic: {message.topic}, Payload: {message.payload.decode('utf-8')}")
    command = message.payload.decode("utf-8")
    
    # 명령 형식이 "play-and-record <url>"인지 확인
    if command.startswith("play-and-record"):
        url = command.split(" ")[1]
        play_and_record(url)
    elif command.startswith("only-play"):
        url = command.split(" ")[1]
        play(url)

# MQTT 연결이 끊어졌을 때 실행되는 콜백 함수
def on_disconnect(client, userdata, rc):
    print(f"Disconnected with return code {rc}. Reconnecting...")
    while True:
        try:
            client.reconnect()
            print("Reconnected to broker.")
            break
        except Exception as e:
            print(f"Reconnection failed: {e}")
            time.sleep(5)  # 5초 후 재시도

# 오디오를 재생하는 함수
def play(url):
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
    wav_filename = "./recorded_audio.wav"
    mp3_filename = "./recorded_audio.mp3"

    # 오디오 녹음 및 MP3로 변환
    record_audio(wav_filename, duration=10)
    convert_to_mp3(wav_filename, mp3_filename)
    upload_file_to_spring(mp3_filename)


# 오디오를 녹음하여 파일로 저장하는 함수
def record_audio(filename, duration=10, sample_rate=44100):
    print("Recording...")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()  # 녹음이 완료될 때까지 대기
    print("Recording complete.")
    sf.write(filename, recording, sample_rate)  # 녹음을 WAV 파일로 저장

# WAV 파일을 MP3로 변환하는 함수
def convert_to_mp3(wav_filename, mp3_filename):
    print("Converting WAV to MP3...")
    os.system(f"ffmpeg -i {wav_filename} {mp3_filename}")
    os.remove(wav_filename)  # 변환 후 원본 WAV 파일 삭제
    print(f"Conversion complete. Saved as {mp3_filename}")


# 파일을 스프링 백엔드로 업로드하는 함수
def upload_file_to_spring(file_path):
    print("Uploading file to Spring backend...")
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'audio/mpeg')}
            response = requests.post(SPRING_BACKEND_URL, files=files)
        if response.status_code == 200:
            print("File uploaded successfully.")
        else:
            print(f"Failed to upload file. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"File upload failed: {e}")
    finally:
        os.remove(file_path)

print("정상실행확인...")

# MQTT 클라이언트 설정
client = mqtt.Client("RaspberryPi_UniqueID")
client.on_message = on_message
client.on_disconnect = on_disconnect

# 브로커 연결
print("Connecting to MQTT broker...")
client.connect(BROKER_ADDRESS, keepalive=60)

# 특정 토픽 구독
print(f"Subscribing to topic: {TOPIC}")
client.subscribe(TOPIC, qos=1)

# MQTT 루프를 별도 스레드에서 실행
print("Starting MQTT loop in a new thread...")
mqtt_thread = threading.Thread(target=client.loop_forever)
mqtt_thread.start()
