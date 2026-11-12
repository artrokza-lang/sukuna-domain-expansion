import vosk
import pyaudio
import json
import threading
from rapidfuzz import fuzz

class VoiceCommandListener:
    def __init__(self, model_path, trigger_phrase="расширение территории", threshold=65):
        self.model = vosk.Model(model_path)
        self.rec = vosk.KaldiRecognizer(self.model, 16000)
        self.trigger_phrase = trigger_phrase.lower().strip()
        self.threshold = threshold
        self.trigger_active = False
        
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8000
        )
        
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()

    def _listen(self):
        while True:
            try:
                data = self.stream.read(4000, exception_on_overflow=False)
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get('text', '').lower().strip()
                    
                    if text:
                        print(f"🎤 Услышано: '{text}'")
                        score = fuzz.partial_ratio(text, self.trigger_phrase)
                        print(f"   -> Совпадение: {score}% (порог: {self.threshold}%)")
                        
                        if score >= self.threshold:
                            print("✅ КОМАНДА РАСПОЗНАНА!")
                            self.trigger_active = True
            except Exception as e:
                print(f"Ошибка аудио-потока: {e}")
                break

    def consume_trigger(self):
        if self.trigger_active:
            self.trigger_active = False
            return True
        return False

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()