# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

import os
import openai
import time
from dotenv import load_dotenv

import json
import gspread

load_dotenv()
# ==== configure OpenAI ====
openai.api_key = os.getenv("OPENAI_API_KEY")

RECIPE = """
INGREDIENTS FOR CHICKEN AVOCADO MANGO SALAD
- 1 1/2 cups or 1/4 head romaine lettuce, rinsed, chopped and spun dry
- 1/4 lb or 1/2 medium cooked chicken breasts 
- 1/4 mango, pitted, peeled and diced
- 1/4 avocado, pitted, peeled and diced
- 1/8 english cucumber sliced 
- 1/8 thinly sliced small purple onion
- 1/8 cup halved cherry tomatoes 
- 1/16 cup chopped cilantro chopped

STEPS
- Step 1: Chop the romaine into bite-sized pieces and discard the core. \
After rinse and spin dry, place it in a large salad bowl. 
- Step 2: Slide chicken into bite size strips and place it over the romaine lettuce.
- Step 3: Place diced mango in to salad bowl.
- Step 4: Peel and dice the advocado, then place it on top of the salad bowl.
- Step 5: Place slices cucumber in to salad bowl.
- Step 6: Added thinly sliced small purple onion.
- Step 7: Cut the cherry tomatoes into half and place it on the salad.
- Step 8: Add chopped fresh cilantro.

INGREDIENTS FOR HONEY VINAIGRETTE DRESSING
- 1/8 cup extra virgin olive oil
- 3/4 Tbsp apple cider vinegar
- 1/2 tsp dijon mustard
- 1/2 tsp honey
- 1/4 garlic clove or 1/4 tsp minced garlic
- 1/4 tsp sea salt
- 1/16 tsp black pepper, or to taste

- Step 9: Combine the Honey Vinaigrette Dressing Ingredients in a mason jar, \
first add olive oil.
- Step 10: Add apple cider vinegar, Dijon mustard and honey
- Step 11: Add garlic, sea salt and black peper
- Step 12: Cover tightly with lid and shake together until well combined. 
- Step 13: Drizzle the salad dressing over the chicken mango avocado salad, adding it to taste.
"""

INSTRUCTIONS = f"""
Your main task is to help guiding user to make the chicken avocado mango salad step \
by step based on the recipe provided delimited by triple backticks. \
The recipe is for 1 person.
Recipe = \'\'\'{RECIPE}\'\'\'

There are 2 parts of this recipe: the salad part and the dressing part.

Please follow these steps to guide user by answering the customer queries.

1:   First decide whether the user is asking a question about a specific \
ingredients or recipe steps or other. When user ask for next step, assume user is about to perform that step. \
Once the dressing steps are finished or all the ingredients are placed, the entire recipe is complete, and no more futher \
steps since all salad and dressing steps and ingredients covered. Congratulate \
user and tell user all the steps are complete.

2:  If the user is asking about overall ingredients, for example: how to make \
the dressing. Respond with all the ingredients without measurements, for \
example: The ingredients for chicken avocado mango salad are romaine \
lettuce, chicken breasts. Do not respond: The ingredients for chicken avocado \
mango salad are 1 lb or 2 medium cooked chicken breasts and 6 cups or 1 head \
romaine lettuce.

3:  If the user is asking about one specific ingredients. Identify whether \
the ingredients is for the salad or the salad dressing, then respond corresponding \
ingredients with measurement. For example: 1/2 thinly sliced small purple \
onion is needed for the salad.

4:  If the user is asking about specific steps, \
identify what step of the recipe the user is working on, then respond with \
short, clear and easy to follow instructions.

5:  Respond to user with summarizing the response from steps above in 30 words or less.\ 
Please response in complete sentence. Please aim to be as helpful, creative, \
friendly, and educative as possible in all of your responses. \
Do not use any external recipe in your responses.\
For question not related to this recipe, try your best to answer it.
"""

TEMPERATURE = 1
MAX_TOKENS = 128
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.2

MAX_CONTEXT_QUESTIONS = 5

CHAT_HISTORY = []

sheet_url = os.getenv("SHEET_URL")
gc = gspread.service_account(filename='credentials.json')
sh = gc.open_by_url(sheet_url)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def myhandler(handler_input):
    # type: (HandlerInput) -> Response
    # speak_output = "Activated Chat G P T Intent"

    #Starting tasks----------------
    worksheet = sh.get_worksheet(0)
    user_questions = worksheet.col_values(1)
    va_responses = worksheet.col_values(2)
    
    if len(user_questions) < 1: # new system: add header
        # this function writes to a cell in the spreadsheet
        worksheet.update("A1", "User Questions")
        worksheet.update("B1", "VA responses")
        
        # 230820 new:
        CHAT_HISTORY.clear()
    # 230820 old:
    # for i in range(1, len(user_questions)):
    #     CHAT_HISTORY.append((user_questions[i], va_responses[i]))
    # 230820 new:
    elif len(user_questions) > 1: # system has already started
        if len(CHAT_HISTORY)==0: # alexa has just restarted:
            for i in range(1, len(user_questions)):
                CHAT_HISTORY.append((user_questions[i], va_responses[i]))

    intent_name = ask_utils.get_intent_name(handler_input)
    separated_intent_name = intent_name.split("Intent")[0]

    if separated_intent_name == "Can":
        separated_intent_name = separated_intent_name + " you"
    elif separated_intent_name == "What":
        separated_intent_name = separated_intent_name + " is"
    elif separated_intent_name == "When":
        separated_intent_name = separated_intent_name + " to"
    elif separated_intent_name == "Whether" or separated_intent_name == "On" or separated_intent_name == "The":
        separated_intent_name = separated_intent_name + " the"
    
    question_value = " "
    if separated_intent_name == "Step":
        question_value = handler_input.request_envelope.request.intent.slots["number"].value
    else:
        question_value = handler_input.request_envelope.request.intent.slots["question"].value
        
    if str(question_value) == "None":
        question_value = " "

    new_question = separated_intent_name + " " + str(question_value)
    
    messages = [
        {"role": "system",
         "content": INSTRUCTIONS},
    ]

    for question, answer in CHAT_HISTORY[-MAX_CONTEXT_QUESTIONS:]:
        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": answer})

    messages.append({"role": "user", "content": new_question})

    completion = ''

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        top_p=1,
        frequency_penalty=FREQUENCY_PENALTY,
        presence_penalty=PRESENCE_PENALTY,
    )

    while completion == '':
        time.sleep(3)

    # get the response and remove the logic (Step X : ...)
    response = completion.choices[0].message.content
    final_response = response.split(":")[-1]
    

    CHAT_HISTORY.append(
        (new_question, final_response))

    worksheet = sh.get_worksheet(0)
    chat_history_filtered = list(
        filter(lambda x: not None, worksheet.col_values(1)))
    new_index = str(len(chat_history_filtered) + 1)
    # this function writes to a cell in the spreadsheet
    worksheet.update("A" + new_index, new_question)
    worksheet.update("B" + new_index, final_response)
    worksheet.update("C" + new_index, intent_name)
    
    break_audio = " <break time=\"10s\" /> "
    sound_bank_audio = "<prosody volume='silent'> . </prosody>"
    speak_output = final_response + break_audio*18 + sound_bank_audio
    ask_output =  "Anything else I can help?" + break_audio*7 + sound_bank_audio

    return (
        handler_input.response_builder
        .speak(speak_output)
        .ask(ask_output)
        .response
    )

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        break_audio = " <break time=\"10s\" /> "
        speak_output = "Welcome to Mango Mango" + break_audio*18 + " Is there anything I can help?"
        ask_output =  "Welcome to Mango Mango" + break_audio*7 + " Is there anything I can help?"

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(ask_output)
            .response
        )


class WhatIntentHandler(AbstractRequestHandler):
    """Handler for What Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("WhatIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class HowIntentHandler(AbstractRequestHandler):
    """Handler for How Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HowIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)
    

class WhenIntentHandler(AbstractRequestHandler):
    """Handler for When Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("WhenIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class WhereIntentHandler(AbstractRequestHandler):
    """Handler for Where Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("WhereIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class WhichIntentHandler(AbstractRequestHandler):
    """Handler for Which Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("WhichIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class WhoIntentHandler(AbstractRequestHandler):
    """Handler for Who Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("WhoIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class IfIntentHandler(AbstractRequestHandler):
    """Handler for If Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("IfIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class WhetherIntentHandler(AbstractRequestHandler):
    """Handler for Whether Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("WhetherIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class DoIntentHandler(AbstractRequestHandler):
    """Handler for Do Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("DoIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class CanIntentHandler(AbstractRequestHandler):
    """Handler for Can Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CanIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class ToIntentHandler(AbstractRequestHandler):
    """Handler for To Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ToIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class TheIntentHandler(AbstractRequestHandler):
    """Handler for To Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("TheIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class OnIntentHandler(AbstractRequestHandler):
    """Handler for On Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("OnIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class HaveIntentHandler(AbstractRequestHandler):
    """Handler for Have Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HaveIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class AreIntentHandler(AbstractRequestHandler):
    """Handler for Are Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AreIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class TellIntentHandler(AbstractRequestHandler):
    """Handler for Tell Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("TellIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class IIntentHandler(AbstractRequestHandler):
    """Handler for To Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("IIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class MyIntentHandler(AbstractRequestHandler):
    """Handler for My Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("MyIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class FirstIntentHandler(AbstractRequestHandler):
    """Handler for First Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("FirstIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class SecondIntentHandler(AbstractRequestHandler):
    """Handler for Second Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("SecondIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class ThirdIntentHandler(AbstractRequestHandler):
    """Handler for Third Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ThirdIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class FourthIntentHandler(AbstractRequestHandler):
    """Handler for Fourth Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("FourthIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class FifthIntentHandler(AbstractRequestHandler):
    """Handler for Fifth Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("FifthIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class SixthIntentHandler(AbstractRequestHandler):
    """Handler for Sixth Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("SixthIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class SeventhIntentHandler(AbstractRequestHandler):
    """Handler for Seventh Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("SeventhIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class EighthIntentHandler(AbstractRequestHandler):
    """Handler for Eighth Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("EighthIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class NinthIntentHandler(AbstractRequestHandler):
    """Handler for Ninth Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("NinthIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class TenthIntentHandler(AbstractRequestHandler):
    """Handler for Tenth Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("TenthIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class EleventhIntentHandler(AbstractRequestHandler):
    """Handler for Eleventh Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("EleventhIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class TwelfthIntentHandler(AbstractRequestHandler):
    """Handler for Twelfth Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("TwelfthIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class ThirteenthIntentHandler(AbstractRequestHandler):
    """Handler for Thirteenth Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ThirteenthIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class NextIntentHandler(AbstractRequestHandler):
    """Handler for Next Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("NextIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class PreviousIntentHandler(AbstractRequestHandler):
    """Handler for Previous Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("PreviousIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class RepeatIntentHandler(AbstractRequestHandler):
    """Handler for Repeat Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("RepeatIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class LastIntentHandler(AbstractRequestHandler):
    """Handler for Last Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("LastIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class StepIntentHandler(AbstractRequestHandler):
    """Handler for Step Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("StepIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class YesIntentHandler(AbstractRequestHandler):
    """Handler for Yes Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("YesIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class SureIntentHandler(AbstractRequestHandler):
    """Handler for Sure Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("SureIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class PleaseIntentHandler(AbstractRequestHandler):
    """Handler for Please Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("PleaseIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class AskChatGPTIntentHandler(AbstractRequestHandler):
    """Handler for AskChatGPT Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AskChatGPTIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class ThankIntentHandler(AbstractRequestHandler):
    """Handler for Thank Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ThankIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class ResumeIntentHandler(AbstractRequestHandler):
    """Handler for Resume Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.ResumeIntent")(handler_input)

    def handle(self, handler_input):
        break_audio = " <break time=\"10s\" /> "
        sound_bank_audio = "<prosody volume='silent'> . </prosody>"
        speak_output = "Sure" + break_audio*18 + sound_bank_audio
        ask_output =  "Anything else I can help?" + break_audio*7 + sound_bank_audio
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(ask_output)
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        break_audio = " <break time=\"10s\" /> "
        sound_bank_audio = "<prosody volume='silent'> . </prosody>"
        speak_output = "How can I help?" + break_audio*18 + sound_bank_audio
        ask_output =  "Anything else I can help?" + break_audio*7 + sound_bank_audio

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(ask_output)
            .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
            .speak(speak_output)
            .response
        )


class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        
        break_audio = " <break time=\"10s\" /> "
        sound_bank_audio = "<prosody volume='silent'> . </prosody>"
        speak_output = "Hmm, I'm not sure. What can I help you with?" + break_audio*18 + sound_bank_audio
        ask_output =  "Anything else I can help?" + break_audio*7 + sound_bank_audio

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(ask_output)
            .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        break_audio = " <break time=\"10s\" /> "
        sound_bank_audio = "<prosody volume='silent'> . </prosody>"
        speak_output = "Hmm, I'm not sure. What can I help you with?" + break_audio*18 + sound_bank_audio
        ask_output =  "Anything else I can help?" + break_audio*7 + sound_bank_audio

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(ask_output)
            .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        break_audio = " <break time=\"10s\" /> "
        sound_bank_audio = "<prosody volume='silent'> . </prosody>"
        speak_output = "Hmm, I'm not sure. What can I help you with?" + break_audio*18 + sound_bank_audio
        ask_output =  "Anything else I can help?" + break_audio*7 + sound_bank_audio
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(ask_output)
            .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
# customized
sb.add_request_handler(WhatIntentHandler())
sb.add_request_handler(HowIntentHandler())
sb.add_request_handler(WhenIntentHandler())
sb.add_request_handler(WhereIntentHandler())
sb.add_request_handler(WhichIntentHandler())
sb.add_request_handler(WhoIntentHandler())
sb.add_request_handler(IfIntentHandler())
sb.add_request_handler(WhetherIntentHandler())
sb.add_request_handler(DoIntentHandler())
sb.add_request_handler(CanIntentHandler())
sb.add_request_handler(ToIntentHandler())
sb.add_request_handler(HaveIntentHandler())
sb.add_request_handler(AreIntentHandler())
sb.add_request_handler(TellIntentHandler())
sb.add_request_handler(TheIntentHandler())
sb.add_request_handler(OnIntentHandler())
sb.add_request_handler(IIntentHandler())
sb.add_request_handler(MyIntentHandler())
sb.add_request_handler(AskChatGPTIntentHandler())
sb.add_request_handler(FirstIntentHandler())
sb.add_request_handler(SecondIntentHandler())
sb.add_request_handler(ThirdIntentHandler())
sb.add_request_handler(FourthIntentHandler())
sb.add_request_handler(FifthIntentHandler())
sb.add_request_handler(SixthIntentHandler())
sb.add_request_handler(SeventhIntentHandler())
sb.add_request_handler(EighthIntentHandler())
sb.add_request_handler(NinthIntentHandler())
sb.add_request_handler(TenthIntentHandler())
sb.add_request_handler(EleventhIntentHandler())
sb.add_request_handler(TwelfthIntentHandler())
sb.add_request_handler(ThirteenthIntentHandler())
sb.add_request_handler(NextIntentHandler())
sb.add_request_handler(PreviousIntentHandler())
sb.add_request_handler(RepeatIntentHandler())
sb.add_request_handler(LastIntentHandler())
sb.add_request_handler(StepIntentHandler())
sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(SureIntentHandler())
sb.add_request_handler(PleaseIntentHandler())
sb.add_request_handler(ThankIntentHandler())

# default
sb.add_request_handler(ResumeIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
# make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers
sb.add_request_handler(IntentReflectorHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
