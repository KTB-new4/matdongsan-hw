import paho.mqtt.client as mqtt
import requests
import sounddevice as sd
import wave
from pydub import AudioSegment
from pydub.playback import play
import io
import os

# URL과 토픽만 수정하면됨. 무한 반복되는 코드임. 또한 녹음이 완료된 파일을 다른 요청으로 전달하는 코드를 추가하면 될것으로 보임.
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

def play_and_record(url):
    # 1. URL에서 오디오 파일 다운로드
    response = requests.get(url)
    audio_data = io.BytesIO(response.content)
    
    # 2. 오디오 파일 재생
    audio = AudioSegment.from_file(audio_data, format="mp3")  # 오디오 포맷에 맞게 설정
    print("Playing audio...")
    play(audio)
    print("Audio playback finished.")

    # 3. 10초간 녹음
    # wav_filename = "./recorded_audio.wav"
    # mp3_filename = "./recorded_audio.mp3"
    # record_audio(wav_filename, duration=10)
    
    # 4. WAV를 MP3로 변환
    # convert_to_mp3(wav_filename, mp3_filename)

def record_audio(filename, duration=10, sample_rate=44100):
    """
    지정된 시간 동안 마이크 입력을 녹음하여 WAV 파일로 저장
    """
    print("Recording...")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()  # 녹음이 완료될 때까지 대기
    print("Recording complete.")

    # 녹음을 WAV 파일로 저장
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16비트 -> 2바이트
        wf.setframerate(sample_rate)
        wf.writeframes(recording.tobytes())

def convert_to_mp3(wav_filename, mp3_filename):
    """
    WAV 파일을 MP3로 변환하고 원본 WAV 파일을 삭제
    """
    print("Converting WAV to MP3...")
    audio = AudioSegment.from_wav(wav_filename)
    audio.export(mp3_filename, format="mp3")
    os.remove(wav_filename)
    print(f"Conversion complete. Saved as {mp3_filename}")

# MQTT 클라이언트 설정
client = mqtt.Client("RaspberryPi")
client.on_message = on_message
client.connect(BROKER_ADDRESS)

# 특정 주제 구독
client.subscribe(TOPIC)

# 메시지 수신 대기
client.loop_forever()
