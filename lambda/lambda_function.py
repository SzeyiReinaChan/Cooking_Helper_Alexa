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
1. INGREDIENTS FOR CHICKEN AVOCADO MANGO SALAD
- 1/4 lb or 1/2 medium cooked chicken breasts 
- 1 1/2 cups or 1/4 head romaine lettuce, rinsed, chopped and spun dry
- 1/8 cup halved cherry tomatoes 
- 1/8 english cucumber sliced 
- 1/4 mango, pitted, peeled and diced
- 1/4 avocado, pitted, peeled and diced
- 1/8 thinly sliced small purple onion
- 1/16 cup chopped cilantro chopped

STEPS
- Step 1: Chop the romaine into bite-sized pieces and discard the core. \
After rinse and spin dry, place it in a large salad bowl. 
- Step 2: Slide chicken into bite size strips and place it over the romaine lettuce.
- Step 3: Place diced mango in to salad bowl.
- Step 4: Peel and dice the advocado, then place it on top of the salad bowl.
- Step 5: Place slices cucumber in to salad bowl.
- Step 6: Added half of a thinly sliced small purple onion.
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
Your task is to help guiding user to make the chicken avocado mango salad step \
by step based on the recipe provided delimited by triple backticks.
Recipe = \'\'\'{RECIPE}\'\'\'

Please follow these steps to guide user by answering the customer queries.

1:   First decide whether the user is \
asking a question about a specific ingredients or recipe steps or other.

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
Do not use any external recipe in your responses.
"""


TEMPERATURE = 1
MAX_TOKENS = 128
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.2

MAX_CONTEXT_QUESTIONS = 5

CHAT_HISTORY = []

sheet_url = "https://docs.google.com/spreadsheets/d/1WHhMP3BVUPYAkrLd6dVFwWQ9QlDAeOYRidMxwWebN9o/"
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
    
    if len(user_questions) < 1:
        # this function writes to a cell in the spreadsheet
        worksheet.update("A1", "User Questions")
        worksheet.update("B1", "VA responses")
        for i in range(1, len(user_questions)):
            CHAT_HISTORY.append((user_questions[i], va_responses[i]))

    intent_name = ask_utils.get_intent_name(handler_input)
    # separated_intent_name = intent_name.split("Intent")[0]
        
    new_question = handler_input.request_envelope.request.intent.slots["question"].value
        
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

    # get the response
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

    return (
        handler_input.response_builder
        .speak(final_response)
        .set_should_end_session(True)
        .response
    )

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Could you repeat the question?"

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


class BuddyIntentHandler(AbstractRequestHandler):
    """Handler for How Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("BuddyIntent")(handler_input)

    def handle(self, handler_input):
        return myhandler(handler_input)


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
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
        speech = "Hmm, I'm not sure. What can I help you with?"
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

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
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
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

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
# customized
sb.add_request_handler(BuddyIntentHandler())
# default
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
# make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers
sb.add_request_handler(IntentReflectorHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
