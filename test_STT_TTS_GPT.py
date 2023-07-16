import speech_recognition as sr
from IPython import embed
print(sr.__version__)
import gtts
from playsound import playsound
import openai, os
import beepy

def get_completion_from_messages(messages, 
                                 model="gpt-3.5-turbo", 
                                 temperature=0, 
                                 max_tokens=500):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature, 
        max_tokens=max_tokens, 
    )
    return response.choices[0].message["content"]

def recognize_speech_from_mic(recognizer, microphone):
    """Transcribe speech from recorded from `microphone`.

    Returns a dictionary with three keys:
    "success": a boolean indicating whether or not the API request was
               successful
    "error":   `None` if no error occured, otherwise a string containing
               an error message if the API could not be reached or
               speech was unrecognizable
    "transcription": `None` if speech could not be transcribed,
               otherwise a string containing the transcribed text
    """
    # check that recognizer and microphone arguments are appropriate type
    if not isinstance(recognizer, sr.Recognizer):
        raise TypeError("`recognizer` must be `Recognizer` instance")

    if not isinstance(microphone, sr.Microphone):
        raise TypeError("`microphone` must be `Microphone` instance")

    # adjust the recognizer sensitivity to ambient noise and record audio
    # from the microphone
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    # set up the response object
    response = {
        "success": True,
        "error": None,
        "transcription": None
    }

    # try recognizing the speech in the recording
    # if a RequestError or UnknownValueError exception is caught,
    #     update the response object accordingly
    try:
        response["transcription"] = recognizer.recognize_google(audio)
    except sr.RequestError:
        # API was unreachable or unresponsive
        response["success"] = False
        response["error"] = "API unavailable"
    except sr.UnknownValueError:
        # speech was unintelligible
        response["error"] = "Unable to recognize speech"

    return response


if __name__ == "__main__":
    # 1. GPT initialization
    # https://medium.com/geekculture/a-simple-guide-to-chatgpt-api-with-python-c147985ae28
    # https://learn.deeplearning.ai/chatgpt-building-system/lesson/6/chaining-prompts
    # OPENAI_API_KEY='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'
    # openai.api_key = os.getenv(OPENAI_API_KEY)
    # completion = openai.ChatCompletion.create(
    #   model="gpt-3.5-turbo",
    #   messages=[
    #     {"role": "user", "content": "Tell the world about the ChatGPT API in the style of a pirate."}
    #   ]
    # )
    # print(completion.choices[0].message.content)
    # embed()

    # 2. Interaction
    # TODO: seems not need to use "Alexa" to initialize the conversation
    while True:
        # https://realpython.com/python-speech-recognition/
        # TODO: use google's API: https://www.youtube.com/watch?v=DtlJH6MgBso, to fine tune e.g., the threshold to detect a complete sentence, punctuation, ...
        # https://cloud.google.com/speech-to-text/docs/speech-to-text-requests
        # https://stackoverflow.com/questions/60742247/when-streaming-is-there-a-limit-to-how-long-a-person-can-consistently-speak-bef
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        ret = recognize_speech_from_mic(recognizer, microphone)

        # Error handling
        if not ret['success']:
            print('1')
            tts = gtts.gTTS("Return unsuccessful.")
            tts.save("tmp.mp3")
            playsound("tmp.mp3")
            # TODO: remove this file.
            continue

        text = ret['transcription']
        if text is None:
            print('2')
            tts = gtts.gTTS("Return None.")
            tts.save("tmp.mp3")
            playsound("tmp.mp3")
            # TODO: remove this file.
            continue

        if "Alexa" not in text:
            print('3')
            tts = gtts.gTTS("You didn't say Alexa.")
            tts.save("tmp.mp3")
            playsound("tmp.mp3")
            # TODO: remove this file.
            continue

        if "exit" in text:
            print('4')
            tts = gtts.gTTS("Bye.")
            tts.save("tmp.mp3")
            playsound("tmp.mp3")
            # TODO: remove this file.
            break

        # Beepy: https://pythonin1minute.com/how-to-beep-in-python/
        # Require installing: https://github.com/greghesp/assistant-relay/issues/49#issuecomment-482837721
        beepy.beep(sound="ping")
        
        # TODO: GPT

        # https://www.thepythoncode.com/article/convert-text-to-speech-in-python
        tts = gtts.gTTS(text + " This is my answer.")
        tts.save("tmp.mp3")
        playsound("tmp.mp3")
        # TODO: remove this file.
        print(text)

        # embed()